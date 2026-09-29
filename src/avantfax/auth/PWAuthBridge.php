<?php
/**
 * AvantFAX Modern Bridge: PWAuthBridge.php
 *
 * Implements legacy PWAuth interface by delegating execution to modern Python auth backend.
 */

class PWAuthBridge
{
    private $python_bin = 'python3';
    private $bridge_script;
    public $debug = false;

    public function __construct() {
        $this->bridge_script = realpath(__DIR__ . '/../db/bridge_cli.py');
    }

    private function call_bridge($request) {
        $json_input = json_encode($request);
        $cmd = escapeshellcmd($this->python_bin) . ' ' . escapeshellarg($this->bridge_script) . ' ' . escapeshellarg($json_input);
        $output = shell_exec($cmd);
        if (!$output) return false;
        return json_decode($output, true);
    }

    public function login($username, $password) {
        $resp = $this->call_bridge(array(
            'action' => 'auth_pwauth',
            'username' => $username,
            'password' => $password
        ));

        return ($resp && !empty($resp['success']));
    }

    public function hashPassword($password) {
        $resp = $this->call_bridge(array(
            'action' => 'hash_password',
            'password' => $password
        ));
        return isset($resp['hash']) ? $resp['hash'] : md5($password);
    }

    public function verifyPassword($plain, $hash) {
        $resp = $this->call_bridge(array(
            'action' => 'verify_password',
            'plain' => $plain,
            'hash' => $hash
        ));
        return ($resp && !empty($resp['matched']));
    }
}
