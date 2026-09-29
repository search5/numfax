<?php
/**
 * AvantFAX Modern Bridge: FaxQueueBridge.php
 *
 * Implements legacy FaxQueue interface by delegating calls to the modern Python FaxQueue service.
 */

class FaxQueue
{
    private $python_bin = 'python3';
    private $bridge_script;
    private $queue = array();

    public function __construct() {
        $this->bridge_script = realpath(__DIR__ . '/../db/bridge_cli.py');
        $this->process_queue();
    }

    private function call_bridge(array $req) {
        $json_input = json_encode($req);
        $cmd = escapeshellcmd($this->python_bin) . ' ' . escapeshellarg($this->bridge_script) . ' ' . escapeshellarg($json_input);
        $output = shell_exec($cmd);
        if (!$output) return false;
        return json_decode($output, true);
    }

    public function process_queue() {
        $resp = $this->call_bridge(array(
            'action' => 'faxqueue',
            'method' => 'get_queue'
        ));
        $this->queue = ($resp && isset($resp['queue'])) ? $resp['queue'] : array();
    }

    public function process_failed_queue() {
        $resp = $this->call_bridge(array(
            'action' => 'faxqueue',
            'method' => 'get_failed_queue'
        ));
        $this->queue = ($resp && isset($resp['queue'])) ? $resp['queue'] : array();
    }

    public function get_queue() {
        return $this->queue;
    }

    public function list_owner($owner) {
        $resp = $this->call_bridge(array(
            'action' => 'faxqueue',
            'method' => 'list_owner',
            'owner' => $owner
        ));
        return ($resp && isset($resp['queue'])) ? $resp['queue'] : array();
    }

    public function killjob($user, $jid) {
        $resp = $this->call_bridge(array(
            'action' => 'faxqueue',
            'method' => 'killjob',
            'user' => $user,
            'jid' => $jid
        ));
        return ($resp && !empty($resp['success']));
    }

    public function faxalter($user, $jid, array $operations) {
        $resp = $this->call_bridge(array(
            'action' => 'faxqueue',
            'method' => 'faxalter',
            'user' => $user,
            'jid' => $jid,
            'operations' => $operations
        ));
        return ($resp && !empty($resp['success']));
    }
}
