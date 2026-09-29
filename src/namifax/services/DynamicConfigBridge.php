<?php
/**
 * AvantFAX Modern Bridge: DynamicConfigBridge.php
 *
 * Implements legacy DynamicConfig interface by delegating calls to the modern Python DynamicConfigService.
 */

class DynamicConfigBridge
{
    private $python_bin = 'python3';
    private $bridge_script;

    private $dynconf_id = null;
    private $device = null;
    private $callid = null;
    private $error = null;

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

    public function get_dynconf_id() {
        return $this->dynconf_id;
    }

    public function get_device() {
        return $this->device;
    }

    public function get_callid() {
        return $this->callid;
    }

    public function get_error() {
        return $this->error;
    }

    public function lookup($device, $callid) {
        $resp = $this->call_bridge(array(
            'action' => 'dynconf',
            'method' => 'lookup',
            'device' => $device,
            'callid' => $callid
        ));

        return ($resp && !empty($resp['match']));
    }

    public function list_rules() {
        $resp = $this->call_bridge(array(
            'action' => 'dynconf',
            'method' => 'list_rules'
        ));

        if ($resp && isset($resp['rules']) && is_array($resp['rules'])) {
            return $resp['rules'];
        }
        return array();
    }

    public function remove($id) {
        $resp = $this->call_bridge(array(
            'action' => 'dynconf',
            'method' => 'remove',
            'id' => $id
        ));

        return ($resp && !empty($resp['success']));
    }

    public function create($device, $callid) {
        $resp = $this->call_bridge(array(
            'action' => 'dynconf',
            'method' => 'create',
            'device' => $device,
            'callid' => $callid
        ));

        if ($resp && !empty($resp['success'])) {
            $this->dynconf_id = $resp['dynconf_id'];
            $this->device = $device;
            $this->callid = $callid;
            $this->error = null;
            return true;
        }

        $this->error = isset($resp['error']) ? $resp['error'] : 'Rule could not be created';
        return false;
    }

    public function load_rule($id) {
        if (!$id) {
            $this->error = 'DynConf not selected';
            return false;
        }

        $resp = $this->call_bridge(array(
            'action' => 'dynconf',
            'method' => 'load',
            'id' => $id
        ));

        if ($resp && !empty($resp['success'])) {
            $this->dynconf_id = $resp['dynconf_id'];
            $this->device = $resp['device'];
            $this->callid = $resp['callid'];
            $this->error = null;
            return true;
        }

        $this->error = isset($resp['error']) ? $resp['error'] : "Rule $id doesn't exist";
        return false;
    }

    public function save_rule($device, $callid) {
        if (!$this->dynconf_id) {
            $this->error = 'DynConf not loaded';
            return false;
        }

        $resp = $this->call_bridge(array(
            'action' => 'dynconf',
            'method' => 'save',
            'id' => $this->dynconf_id,
            'device' => $device,
            'callid' => $callid
        ));

        if ($resp && !empty($resp['success'])) {
            $this->device = $device;
            $this->callid = $callid;
            $this->error = null;
            return true;
        }

        $this->error = isset($resp['error']) ? $resp['error'] : 'Failed to save rule';
        return false;
    }
}
