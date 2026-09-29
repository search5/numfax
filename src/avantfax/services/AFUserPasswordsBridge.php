<?php
/**
 * AvantFAX Modern Bridge: AFUserPasswordsBridge.php
 *
 * Implements legacy AFUserPasswords interface by delegating calls to the modern Python PasswordHistoryService.
 */

class AFUserPasswordsBridge
{
    private $python_bin = 'python3';
    private $bridge_script;

    protected $upid, $uid, $pwdhash;

    public function __construct() {
        $this->bridge_script = realpath(__DIR__ . '/../db/bridge_cli.py');
    }

    private function call_bridge(array $req) {
        $json_input = json_encode($req);
        $cmd = escapeshellcmd($this->python_bin) . ' ' . escapeshellarg($this->bridge_script) . ' ' . escapeshellarg($json_input);
        $output = shell_exec($cmd);
        if (!$output) return false;
        return json_decode($output, true);
    }

    public function log_password($pwd, $uid) {
        $resp = $this->call_bridge(array(
            'action' => 'user_passwords',
            'method' => 'log_password',
            'pwd' => $pwd,
            'uid' => $uid
        ));

        return ($resp && !empty($resp['success']));
    }

    public function password_used($pwd, $uid) {
        $resp = $this->call_bridge(array(
            'action' => 'user_passwords',
            'method' => 'password_used',
            'pwd' => $pwd,
            'uid' => $uid
        ));

        return ($resp && !empty($resp['used']));
    }

    public function clear_hashes($uid) {
        $resp = $this->call_bridge(array(
            'action' => 'user_passwords',
            'method' => 'clear_hashes',
            'uid' => $uid
        ));

        return ($resp && !empty($resp['success']));
    }
}
