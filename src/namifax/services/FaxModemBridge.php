<?php
/**
 * AvantFAX Modern Bridge: FaxModemBridge.php
 *
 * Implements legacy FaxModem interface by delegating calls to the modern Python FaxModemService.
 */

class FaxModemBridge
{
    private $python_bin = 'python3';
    private $bridge_script;

    private $devid    = null;
    private $alias    = null;
    private $device   = null;
    private $contact  = null;
    private $printer  = null;
    private $faxcatid = null;
    private $error    = null;

    private $cached_list = null;
    private $list_index = 0;

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

    public function create($device, $alias, $contact = null, $printer = null, $faxcatid = null) {
        $resp = $this->call_bridge(array(
            'action' => 'modem',
            'method' => 'create',
            'device' => $device,
            'alias' => $alias,
            'contact' => $contact,
            'printer' => $printer,
            'faxcatid' => $faxcatid
        ));

        if ($resp && !empty($resp['success'])) {
            $this->devid = $resp['devid'];
            $this->device = $device;
            $this->alias = $alias;
            $this->contact = $contact;
            $this->printer = $printer;
            $this->faxcatid = $faxcatid;
            $this->error = null;
            return true;
        }

        $this->error = isset($resp['error']) ? $resp['error'] : 'Modem could not be created';
        return false;
    }

    public function delete_device($device) {
        $resp = $this->call_bridge(array(
            'action' => 'modem',
            'method' => 'delete',
            'device' => $device
        ));

        return ($resp && !empty($resp['success']));
    }

    public function get_modems() {
        $resp = $this->call_bridge(array(
            'action' => 'modem',
            'method' => 'get_modems'
        ));

        if ($resp && isset($resp['modems']) && is_array($resp['modems'])) {
            $this->error = null;
            return $resp['modems'];
        }

        $this->error = isset($resp['error']) ? $resp['error'] : 'No modems configured';
        return null;
    }

    public function list_modems(&$devid, &$alias, &$device) {
        if ($this->cached_list === null) {
            $resp = $this->call_bridge(array(
                'action' => 'modem',
                'method' => 'list_all'
            ));
            $this->cached_list = ($resp && isset($resp['modems']) && is_array($resp['modems'])) ? $resp['modems'] : array();
            $this->list_index = 0;
        }

        if (isset($this->cached_list[$this->list_index])) {
            $item = $this->cached_list[$this->list_index++];
            $devid = $item['devid'];
            $alias = $item['alias'];
            $device = $item['device'];
            return true;
        }

        $this->cached_list = null;
        $this->list_index = 0;
        $this->error = 'No modems configured';
        return false;
    }

    public function load_device($device) {
        if (!$device) {
            $this->error = 'Modem not selected';
            return false;
        }

        $resp = $this->call_bridge(array(
            'action' => 'modem',
            'method' => 'load',
            'device' => $device
        ));

        if ($resp && !empty($resp['success'])) {
            $this->devid = $resp['devid'];
            $this->alias = $resp['alias'];
            $this->device = $resp['device'];
            $this->contact = $resp['contact'];
            $this->printer = $resp['printer'];
            $this->faxcatid = $resp['faxcatid'];
            $this->error = null;
            return true;
        }

        $this->error = isset($resp['error']) ? $resp['error'] : "Modem '$device' doesn't exist";
        return false;
    }

    public function loadbyid($devid) {
        if (!$devid) {
            $this->error = 'Modem not selected';
            return false;
        }

        $resp = $this->call_bridge(array(
            'action' => 'modem',
            'method' => 'loadbyid',
            'devid' => $devid
        ));

        if ($resp && !empty($resp['success'])) {
            $this->devid = $resp['devid'];
            $this->alias = $resp['alias'];
            $this->device = $resp['device'];
            $this->contact = $resp['contact'];
            $this->printer = $resp['printer'];
            $this->faxcatid = $resp['faxcatid'];
            $this->error = null;
            return true;
        }

        $this->error = isset($resp['error']) ? $resp['error'] : "Modem '$devid' doesn't exist";
        return false;
    }

    public function get_status() {
        if (!$this->device) {
            return array('class' => 'modem-wait', 'status' => 'Please wait');
        }

        $resp = $this->call_bridge(array(
            'action' => 'modem',
            'method' => 'get_status',
            'device' => $this->device
        ));

        if ($resp && isset($resp['status'])) {
            return $resp['status'];
        }

        return array('class' => 'modem-wait', 'status' => 'Please wait');
    }

    public function get_alias()    { return $this->alias; }
    public function get_contact()  { return $this->contact; }
    public function get_printer()  { return $this->printer; }
    public function get_faxcatid() { return $this->faxcatid; }
    public function get_devid()    { return $this->devid; }
    public function get_device()   { return $this->device; }
    public function get_error()    { return $this->error; }

    public function set_alias($alias) {
        if (!$this->devid) { $this->error = 'No modem loaded'; return false; }
        $resp = $this->call_bridge(array('action' => 'modem', 'method' => 'update', 'devid' => $this->devid, 'field' => 'alias', 'value' => $alias));
        if ($resp && !empty($resp['success'])) { $this->alias = $alias; return true; }
        return false;
    }

    public function set_contact($contact) {
        if (!$this->devid) { $this->error = 'No modem loaded'; return false; }
        $resp = $this->call_bridge(array('action' => 'modem', 'method' => 'update', 'devid' => $this->devid, 'field' => 'contact', 'value' => $contact));
        if ($resp && !empty($resp['success'])) { $this->contact = $contact; return true; }
        return false;
    }

    public function set_printer($printer) {
        if (!$this->devid) { $this->error = 'No modem loaded'; return false; }
        $resp = $this->call_bridge(array('action' => 'modem', 'method' => 'update', 'devid' => $this->devid, 'field' => 'printer', 'value' => $printer));
        if ($resp && !empty($resp['success'])) { $this->printer = $printer; return true; }
        return false;
    }

    public function set_faxcatid($faxcatid) {
        if (!$this->devid) { $this->error = 'No modem loaded'; return false; }
        $resp = $this->call_bridge(array('action' => 'modem', 'method' => 'update', 'devid' => $this->devid, 'field' => 'faxcatid', 'value' => $faxcatid));
        if ($resp && !empty($resp['success'])) { $this->faxcatid = $faxcatid; return true; }
        return false;
    }
}
