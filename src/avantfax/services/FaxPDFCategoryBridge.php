<?php
/**
 * AvantFAX Modern Bridge: FaxPDFCategoryBridge.php
 *
 * Implements legacy FaxPDFCategory interface by delegating calls to the modern Python CategoryService.
 */

class FaxPDFCategoryBridge
{
    private $python_bin = 'python3';
    private $bridge_script;
    private $error = null;
    
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

    public function create($name) {
        $resp = $this->call_bridge(array(
            'action' => 'categories',
            'method' => 'create',
            'name' => $name
        ));

        if ($resp && !empty($resp['success'])) {
            $this->error = null;
            return true;
        }

        $this->error = isset($resp['error']) ? $resp['error'] : 'Category could not be created';
        return false;
    }

    public function set_name($name, $catid) {
        if (!$name || !$catid) {
            $this->error = 'No name or catid to set';
            return false;
        }

        $resp = $this->call_bridge(array(
            'action' => 'categories',
            'method' => 'set_name',
            'name' => $name,
            'catid' => $catid
        ));

        if ($resp && !empty($resp['success'])) {
            $this->error = null;
            return true;
        }

        $this->error = isset($resp['error']) ? $resp['error'] : 'Failed to update category name';
        return false;
    }

    public function get_list(&$catid, &$name) {
        if ($this->cached_list === null) {
            $resp = $this->call_bridge(array(
                'action' => 'categories',
                'method' => 'get_categories'
            ));
            $this->cached_list = ($resp && isset($resp['categories']) && is_array($resp['categories'])) ? $resp['categories'] : array();
            $this->list_index = 0;
        }

        if (isset($this->cached_list[$this->list_index])) {
            $item = $this->cached_list[$this->list_index++];
            $catid = $item['catid'];
            $name = $item['name'];
            return true;
        }

        $this->cached_list = null;
        $this->list_index = 0;
        return false;
    }

    public function get_categories() {
        $resp = $this->call_bridge(array(
            'action' => 'categories',
            'method' => 'get_categories'
        ));

        if ($resp && isset($resp['categories']) && is_array($resp['categories'])) {
            $this->error = null;
            return $resp['categories'];
        }

        $this->error = isset($resp['error']) ? $resp['error'] : null;
        return null;
    }

    public function get_name($catid) {
        if (!$catid) {
            $this->error = 'No catid sent';
            return null;
        }

        $resp = $this->call_bridge(array(
            'action' => 'categories',
            'method' => 'get_name',
            'catid' => $catid
        ));

        if ($resp && isset($resp['name']) && $resp['name'] !== null) {
            $this->error = null;
            return $resp['name'];
        }

        $this->error = isset($resp['error']) ? $resp['error'] : null;
        return null;
    }

    public function delete_category($catid) {
        if (!$catid) {
            $this->error = 'No catid sent';
            return null;
        }

        $resp = $this->call_bridge(array(
            'action' => 'categories',
            'method' => 'delete',
            'catid' => $catid
        ));

        if ($resp && !empty($resp['success'])) {
            $this->error = null;
            return true;
        }

        $this->error = isset($resp['error']) ? $resp['error'] : 'Failed to delete category';
        return false;
    }

    public function get_error() {
        return $this->error;
    }
}
