<?php
/**
 * AvantFAX Modern Bridge: DIDRoutingBridge.php
 *
 * Implements legacy DIDRouting interface by delegating calls to the modern Python DIDRoutingService.
 */

class DIDRoutingBridge
{
    private $python_bin = 'python3';
    private $bridge_script;

    private $didr_id   = null;
    private $alias     = null;
    private $contact   = null;
    private $routecode = null;
    private $faxcatid  = null;
    private $printer   = null;
    private $error     = null;

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

    public function create($route, $alias, $contact = null, $printer = null, $faxcatid = null) {
        $resp = $this->call_bridge(array(
            'action' => 'did',
            'method' => 'create',
            'route' => $route,
            'alias' => $alias,
            'contact' => $contact,
            'printer' => $printer,
            'faxcatid' => $faxcatid
        ));

        if ($resp && !empty($resp['success'])) {
            $this->didr_id = $resp['didr_id'];
            $this->routecode = $route;
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
            'action' => 'did',
            'method' => 'delete',
            'didr_id' => $id
        ));

        return ($resp && !empty($resp['success']));
    }

    public function get_routes() {
        $resp = $this->call_bridge(array(
            'action' => 'did',
            'method' => 'get_routes'
        ));

        if ($resp && isset($resp['routes']) && is_array($resp['routes'])) {
            $this->error = null;
            return $resp['routes'];
        }

        $this->error = isset($resp['error']) ? $resp['error'] : 'No DID routes configured';
        return null;
    }

    public function list_routes(&$didr_id, &$alias, &$routecode) {
        if ($this->cached_list === null) {
            $resp = $this->call_bridge(array(
                'action' => 'did',
                'method' => 'list_all'
            ));
            $this->cached_list = ($resp && isset($resp['routes']) && is_array($resp['routes'])) ? $resp['routes'] : array();
            $this->list_index = 0;
        }

        if (isset($this->cached_list[$this->list_index])) {
            $item = $this->cached_list[$this->list_index++];
            $didr_id = $item['didr_id'];
            $alias = $item['alias'];
            $routecode = $item['routecode'];
            return true;
        }

        $this->cached_list = null;
        $this->list_index = 0;
        $this->error = 'No DID routes configured';
        return false;
    }

    public function load_route($routecode) {
        if (!$routecode) {
            $this->error = 'Route code not selected';
            return false;
        }

        $resp = $this->call_bridge(array(
            'action' => 'did',
            'method' => 'load_route',
            'route' => $routecode
        ));

        if ($resp && !empty($resp['success'])) {
            $this->didr_id = $resp['didr_id'];
            $this->alias = $resp['alias'];
            $this->routecode = $resp['routecode'];
            $this->contact = $resp['contact'];
            $this->printer = $resp['printer'];
            $this->faxcatid = $resp['faxcatid'];
            $this->error = null;
            return true;
        }

        $this->error = isset($resp['error']) ? $resp['error'] : "DID route '$routecode' doesn't exist";
        return false;
    }

    public function loadbyid($didr_id) {
        if (!$didr_id) {
            $this->error = 'Route ID not selected';
            return false;
        }

        $resp = $this->call_bridge(array(
            'action' => 'did',
            'method' => 'loadbyid',
            'didr_id' => $didr_id
        ));

        if ($resp && !empty($resp['success'])) {
            $this->didr_id = $resp['didr_id'];
            $this->alias = $resp['alias'];
            $this->routecode = $resp['routecode'];
            $this->contact = $resp['contact'];
            $this->printer = $resp['printer'];
            $this->faxcatid = $resp['faxcatid'];
            $this->error = null;
            return true;
        }

        $this->error = isset($resp['error']) ? $resp['error'] : "DID route '$didr_id' doesn't exist";
        return false;
    }

    public function get_alias()      { return $this->alias; }
    public function get_contact()    { return $this->contact; }
    public function get_printer()    { return $this->printer; }
    public function get_faxcatid()   { return $this->faxcatid; }
    public function get_didr_id()    { return $this->didr_id; }
    public function get_route()      { return $this->routecode; }
    public function get_error()      { return $this->error; }

    public function set_alias($alias) {
        if (!$this->didr_id) { $this->error = 'No entry loaded'; return false; }
        $resp = $this->call_bridge(array('action' => 'did', 'method' => 'update', 'didr_id' => $this->didr_id, 'field' => 'alias', 'value' => $alias));
        if ($resp && !empty($resp['success'])) { $this->alias = $alias; return true; }
        return false;
    }

    public function set_routecode($routecode) {
        if (!$this->didr_id) { $this->error = 'No entry loaded'; return false; }
        $resp = $this->call_bridge(array('action' => 'did', 'method' => 'update', 'didr_id' => $this->didr_id, 'field' => 'routecode', 'value' => $routecode));
        if ($resp && !empty($resp['success'])) { $this->routecode = $routecode; return true; }
        return false;
    }

    public function set_contact($contact) {
        if (!$this->didr_id) { $this->error = 'No entry loaded'; return false; }
        $resp = $this->call_bridge(array('action' => 'did', 'method' => 'update', 'didr_id' => $this->didr_id, 'field' => 'contact', 'value' => $contact));
        if ($resp && !empty($resp['success'])) { $this->contact = $contact; return true; }
        return false;
    }

    public function set_printer($printer) {
        if (!$this->didr_id) { $this->error = 'No entry loaded'; return false; }
        $resp = $this->call_bridge(array('action' => 'did', 'method' => 'update', 'didr_id' => $this->didr_id, 'field' => 'printer', 'value' => $printer));
        if ($resp && !empty($resp['success'])) { $this->printer = $printer; return true; }
        return false;
    }

    public function set_faxcatid($faxcatid) {
        if (!$this->didr_id) { $this->error = 'No entry loaded'; return false; }
        $resp = $this->call_bridge(array('action' => 'did', 'method' => 'update', 'didr_id' => $this->didr_id, 'field' => 'faxcatid', 'value' => $faxcatid));
        if ($resp && !empty($resp['success'])) { $this->faxcatid = $faxcatid; return true; }
        return false;
    }
}
