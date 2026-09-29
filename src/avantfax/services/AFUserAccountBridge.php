<?php
/**
 * AvantFAX Modern Bridge: AFUserAccountBridge.php
 *
 * Implements legacy AFUserAccount interface by delegating calls to the modern Python UserAccountService.
 */

class AFUserAccount
{
    private $python_bin = 'python3';
    private $bridge_script;

    protected $uid;
    protected $dbdata = array();

    private $error;
    private $logged_in = false;
    private $admin_logged_in = false;
    private $pwdexpired = false;
    private $accounts_list = null;

    public function __construct() {
        $this->bridge_script = realpath(__DIR__ . '/../db/bridge_cli.py');
    }

    private function call_bridge(array $req) {
        if ($this->uid && !isset($req['uid'])) {
            $req['uid'] = $this->uid;
        }
        $json_input = json_encode($req);
        $cmd = escapeshellcmd($this->python_bin) . ' ' . escapeshellarg($this->bridge_script) . ' ' . escapeshellarg($json_input);
        $output = shell_exec($cmd);
        if (!$output) return false;
        return json_decode($output, true);
    }

    public function init_db() {
        if ($this->uid) {
            $this->load($this->uid);
        }
    }

    public function create(array $details) {
        $resp = $this->call_bridge(array(
            'action' => 'user_account',
            'method' => 'create',
            'details' => $details
        ));

        if ($resp && !empty($resp['success'])) {
            $this->uid = $resp['uid'];
            $this->dbdata = $details;
            $this->dbdata['uid'] = $this->uid;
            $this->error = null;
            return true;
        }

        $this->error = isset($resp['error']) ? $resp['error'] : 'Account creation failed';
        return false;
    }

    public function list_accounts() {
        if ($this->accounts_list === null) {
            $resp = $this->call_bridge(array(
                'action' => 'user_account',
                'method' => 'list_accounts'
            ));
            $this->accounts_list = ($resp && isset($resp['accounts'])) ? $resp['accounts'] : array();
        }

        if (is_array($this->accounts_list) && count($this->accounts_list) > 0) {
            $data = array_shift($this->accounts_list);
            $this->load_vals($data);
            return true;
        }

        $this->accounts_list = null;
        return false;
    }

    public function update() {
        if (!$this->uid) { $this->error = "No uid set"; return false; }
        $resp = $this->call_bridge(array(
            'action' => 'user_account',
            'method' => 'update',
            'data' => $this->dbdata
        ));
        return ($resp && !empty($resp['success']));
    }

    public function user_update() {
        return $this->update();
    }

    public function change_password($pwd) {
        if (!$this->uid) { $this->error = "No uid set"; return false; }
        $resp = $this->call_bridge(array(
            'action' => 'user_account',
            'method' => 'change_password',
            'pwd' => $pwd
        ));
        if ($resp && !empty($resp['success'])) {
            $this->error = null;
            return true;
        }
        $this->error = isset($resp['error']) ? $resp['error'] : 'Failed to change password';
        return false;
    }

    public function reset_password($email) {
        $resp = $this->call_bridge(array(
            'action' => 'user_account',
            'method' => 'reset_password',
            'email' => $email
        ));
        if ($resp && !empty($resp['success'])) {
            $this->error = null;
            return true;
        }
        $this->error = isset($resp['error']) ? $resp['error'] : 'Failed to reset password';
        return false;
    }

    public function set_newpassword($oldpwd, $newpwd) {
        if (!$this->uid) { $this->error = "No uid set"; return false; }
        $resp = $this->call_bridge(array(
            'action' => 'user_account',
            'method' => 'set_newpassword',
            'oldpwd' => $oldpwd,
            'newpwd' => $newpwd
        ));
        if ($resp && !empty($resp['success'])) {
            $this->error = null;
            return true;
        }
        $this->error = isset($resp['error']) ? $resp['error'] : 'Failed to set new password';
        return false;
    }

    public function login($username, $password, $admin = false) {
        $resp = $this->call_bridge(array(
            'action' => 'user_account',
            'method' => 'login',
            'username' => $username,
            'password' => $password,
            'admin' => $admin,
            'remote_ip' => isset($_SERVER['REMOTE_ADDR']) ? $_SERVER['REMOTE_ADDR'] : '127.0.0.1'
        ));

        if ($resp && !empty($resp['success'])) {
            $this->logged_in = true;
            $this->admin_logged_in = !empty($resp['admin_logged_in']);
            $this->pwdexpired = !empty($resp['is_expired']);
            $this->uid = $resp['uid'];
            $this->load_vals($resp['values']);
            $this->error = null;
            return true;
        }

        $this->logged_in = false;
        $this->admin_logged_in = false;
        $this->error = isset($resp['error']) ? $resp['error'] : 'Login failed';
        return false;
    }

    public function login_webauth($username, $admin = false) {
        $resp = $this->call_bridge(array(
            'action' => 'user_account',
            'method' => 'login_webauth',
            'username' => $username,
            'admin' => $admin,
            'remote_ip' => isset($_SERVER['REMOTE_ADDR']) ? $_SERVER['REMOTE_ADDR'] : '127.0.0.1'
        ));

        if ($resp && !empty($resp['success'])) {
            $this->logged_in = true;
            $this->admin_logged_in = !empty($resp['admin_logged_in']);
            $this->uid = $resp['uid'];
            $this->load_vals($resp['values']);
            $this->error = null;
            return true;
        }

        $this->logged_in = false;
        $this->error = isset($resp['error']) ? $resp['error'] : 'Webauth login failed';
        return false;
    }

    public function load($userid) {
        if (!$userid) { $this->error = "No userid"; return false; }
        $resp = $this->call_bridge(array(
            'action' => 'user_account',
            'method' => 'load',
            'userid' => $userid
        ));

        if ($resp && !empty($resp['success'])) {
            $this->load_vals($resp['values']);
            $this->uid = $resp['uid'];
            $this->error = null;
            return true;
        }

        $this->error = isset($resp['error']) ? $resp['error'] : "Invalid userid";
        return false;
    }

    public function load_username($username) {
        if (!$username) { $this->error = "No username"; return false; }
        $resp = $this->call_bridge(array(
            'action' => 'user_account',
            'method' => 'load_username',
            'username' => $username
        ));

        if ($resp && !empty($resp['success'])) {
            $this->load_vals($resp['values']);
            $this->uid = $resp['uid'];
            $this->error = null;
            return true;
        }

        $this->error = isset($resp['error']) ? $resp['error'] : "Invalid username";
        return false;
    }

    public function loadbyemail($email) {
        if (!$email) { $this->error = "No email"; return false; }
        $resp = $this->call_bridge(array(
            'action' => 'user_account',
            'method' => 'loadbyemail',
            'email' => $email
        ));

        if ($resp && !empty($resp['success'])) {
            $this->load_vals($resp['values']);
            $this->uid = $resp['uid'];
            $this->error = null;
            return true;
        }

        $this->error = isset($resp['error']) ? $resp['error'] : "Invalid email";
        return false;
    }

    public function remove($userid) {
        $resp = $this->call_bridge(array(
            'action' => 'user_account',
            'method' => 'remove',
            'userid' => $userid
        ));
        return ($resp && !empty($resp['success']));
    }

    public function get_error()           { return $this->error; }
    public function is_expired()          { return $this->pwdexpired; }
    public function check_login()         { return $this->logged_in; }
    public function check_admin_login()   { return $this->admin_logged_in; }
    public function get_uid()             { return $this->uid; }
    public function get_allvalues()       { return $this->dbdata; }

    public function get_modemdevs() {
        if (isset($this->dbdata['modemdevs']) && $this->dbdata['modemdevs'] !== '') {
            return explode("|", $this->dbdata['modemdevs']);
        }
        return array();
    }

    public function set_modemdevs(array $val = NULL) {
        if (!$this->uid) return false;
        $this->dbdata['modemdevs'] = ($val && count($val)) ? implode("|", $val) : NULL;
        return true;
    }

    public function get_faxcats() {
        if (isset($this->dbdata['faxcats']) && $this->dbdata['faxcats'] !== '') {
            return explode("|", $this->dbdata['faxcats']);
        }
        return array();
    }

    public function set_faxcats(array $val = NULL) {
        if (!$this->uid) return false;
        $this->dbdata['faxcats'] = ($val && count($val)) ? implode("|", $val) : NULL;
        return true;
    }

    public function get_didrouting() {
        if (isset($this->dbdata['didrouting']) && $this->dbdata['didrouting'] !== '') {
            return explode("|", $this->dbdata['didrouting']);
        }
        return array();
    }

    public function set_didrouting(array $val = NULL) {
        if (!$this->uid) return false;
        $this->dbdata['didrouting'] = ($val && count($val)) ? implode("|", $val) : NULL;
        return true;
    }

    public function set_username($username) {
        if (!$this->uid) return false;
        $this->dbdata['username'] = $username;
        return true;
    }

    public function set_email($email) {
        if (!$this->uid) return false;
        $this->dbdata['email'] = $email;
        return true;
    }

    public function __get($varname) {
        if (array_key_exists($varname, $this->dbdata)) {
            return html_entity_decode($this->dbdata[$varname], ENT_QUOTES, "UTF-8");
        }
        return NULL;
    }

    public function __set($varname, $value) {
        $this->dbdata[$varname] = $value;
    }

    private function load_vals(array $data) {
        $this->dbdata = array_merge($this->dbdata, $data);
        if (isset($this->dbdata['uid'])) {
            $this->uid = $this->dbdata['uid'];
        }
    }
}
