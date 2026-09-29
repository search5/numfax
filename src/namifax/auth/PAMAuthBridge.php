<?php
/**
 * AvantFAX Modern Bridge: PAMAuthBridge.php
 *
 * Implements legacy PAMAuth interface by delegating authentication to modern Python PAM backend.
 */

class PAMAuthBridge
{
    private $python_bin = 'python3';
    private $bridge_script;
    private $service = 'login';
    public $debug = false;

    public function __construct($service = 'login') {
        $this->bridge_script = realpath(__DIR__ . '/../db/bridge_cli.py');
        $this->service = $service;
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
            'action' => 'auth_pam',
            'username' => $username,
            'password' => $password,
            'service' => $this->service
        ));

        return ($resp && !empty($resp['success']));
    }
}
