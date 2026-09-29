<?php
/**
 * AvantFAX Modern Bridge: BarcodeRoutingBridge.php
 *
 * Implements legacy BarcodeRouting interface by delegating calls to the modern Python BarcodeRoutingService.
 */

class BarcodeRoutingBridge
{
    private $python_bin = 'python3';
    private $bridge_script;

    private $barcode_id = null;
    private $alias      = null;
    private $contact    = null;
    private $barcode    = null;
    private $faxcatid   = null;
    private $printer    = null;
    private $error      = null;

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

    public function create($barcode, $alias, $contact = null, $printer = null, $faxcatid = null) {
        $resp = $this->call_bridge(array(
            'action' => 'barcode',
            'method' => 'create',
            'barcode' => $barcode,
            'alias' => $alias,
            'contact' => $contact,
            'printer' => $printer,
            'faxcatid' => $faxcatid
        ));

        if ($resp && !empty($resp['success'])) {
            $this->barcode_id = $resp['barcode_id'];
            $this->barcode = $barcode;
            $this->alias = $alias;
            $this->contact = $contact;
            $this->printer = $printer;
            $this->faxcatid = $faxcatid;
            $this->error = null;
            return true;
        }

        $this->error = isset($resp['error']) ? $resp['error'] : 'Route could not be created';
        return false;
    }

    public function delete_route($id) {
        $resp = $this->call_bridge(array(
            'action' => 'barcode',
            'method' => 'delete',
            'barcode_id' => $id
        ));

        return ($resp && !empty($resp['success']));
    }

    public function get_routes() {
        $resp = $this->call_bridge(array(
            'action' => 'barcode',
            'method' => 'get_routes'
        ));

        if ($resp && isset($resp['routes']) && is_array($resp['routes'])) {
            $this->error = null;
            return $resp['routes'];
        }

        $this->error = isset($resp['error']) ? $resp['error'] : 'No barcode routes configured';
        return null;
    }

    public function list_routes(&$barcode_id, &$alias, &$barcode) {
        if ($this->cached_list === null) {
            $resp = $this->call_bridge(array(
                'action' => 'barcode',
                'method' => 'list_all'
            ));
            $this->cached_list = ($resp && isset($resp['routes']) && is_array($resp['routes'])) ? $resp['routes'] : array();
            $this->list_index = 0;
        }

        if (isset($this->cached_list[$this->list_index])) {
            $item = $this->cached_list[$this->list_index++];
            $barcode_id = $item['barcode_id'];
            $alias = $item['alias'];
            $barcode = $item['barcode'];
            return true;
        }

        $this->cached_list = null;
        $this->list_index = 0;
        $this->error = 'No barcode routes configured';
        return false;
    }

    public function load_route($barcode) {
        if (!$barcode) {
            $this->error = 'Barcode not selected';
            return false;
        }

        $resp = $this->call_bridge(array(
            'action' => 'barcode',
            'method' => 'load_route',
            'barcode' => $barcode
        ));

        if ($resp && !empty($resp['success'])) {
            $this->barcode_id = $resp['barcode_id'];
            $this->alias = $resp['alias'];
            $this->barcode = $resp['barcode'];
            $this->contact = $resp['contact'];
            $this->printer = $resp['printer'];
            $this->faxcatid = $resp['faxcatid'];
            $this->error = null;
            return true;
        }

        $this->error = isset($resp['error']) ? $resp['error'] : "Barcode route '$barcode' doesn't exist";
        return false;
    }

    public function loadbyid($barcode_id) {
        if (!$barcode_id) {
            $this->error = 'Barcode ID not selected';
            return false;
        }

        $resp = $this->call_bridge(array(
            'action' => 'barcode',
            'method' => 'loadbyid',
            'barcode_id' => $barcode_id
        ));

        if ($resp && !empty($resp['success'])) {
            $this->barcode_id = $resp['barcode_id'];
            $this->alias = $resp['alias'];
            $this->barcode = $resp['barcode'];
            $this->contact = $resp['contact'];
            $this->printer = $resp['printer'];
            $this->faxcatid = $resp['faxcatid'];
            $this->error = null;
            return true;
        }

        $this->error = isset($resp['error']) ? $resp['error'] : "Barcode route '$barcode_id' doesn't exist";
        return false;
    }

    public function get_alias()      { return $this->alias; }
    public function get_contact()    { return $this->contact; }
    public function get_printer()    { return $this->printer; }
    public function get_faxcatid()   { return $this->faxcatid; }
    public function get_barcode_id() { return $this->barcode_id; }
    public function get_barcode()    { return $this->barcode; }
    public function get_error()      { return $this->error; }

    public function set_alias($alias) {
        if (!$this->barcode_id) { $this->error = 'No entry loaded'; return false; }
        $resp = $this->call_bridge(array('action' => 'barcode', 'method' => 'update', 'barcode_id' => $this->barcode_id, 'field' => 'alias', 'value' => $alias));
        if ($resp && !empty($resp['success'])) { $this->alias = $alias; return true; }
        return false;
    }

    public function set_barcode($barcode) {
        if (!$this->barcode_id) { $this->error = 'No entry loaded'; return false; }
        $resp = $this->call_bridge(array('action' => 'barcode', 'method' => 'update', 'barcode_id' => $this->barcode_id, 'field' => 'barcode', 'value' => $barcode));
        if ($resp && !empty($resp['success'])) { $this->barcode = $barcode; return true; }
        return false;
    }

    public function set_contact($contact) {
        if (!$this->barcode_id) { $this->error = 'No entry loaded'; return false; }
        $resp = $this->call_bridge(array('action' => 'barcode', 'method' => 'update', 'barcode_id' => $this->barcode_id, 'field' => 'contact', 'value' => $contact));
        if ($resp && !empty($resp['success'])) { $this->contact = $contact; return true; }
        return false;
    }

    public function set_printer($printer) {
        if (!$this->barcode_id) { $this->error = 'No entry loaded'; return false; }
        $resp = $this->call_bridge(array('action' => 'barcode', 'method' => 'update', 'barcode_id' => $this->barcode_id, 'field' => 'printer', 'value' => $printer));
        if ($resp && !empty($resp['success'])) { $this->printer = $printer; return true; }
        return false;
    }

    public function set_faxcatid($faxcatid) {
        if (!$this->barcode_id) { $this->error = 'No entry loaded'; return false; }
        $resp = $this->call_bridge(array('action' => 'barcode', 'method' => 'update', 'barcode_id' => $this->barcode_id, 'field' => 'faxcatid', 'value' => $faxcatid));
        if ($resp && !empty($resp['success'])) { $this->faxcatid = $faxcatid; return true; }
        return false;
    }
}
