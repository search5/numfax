<?php
/**
 * AvantFAX Modern Bridge: CoversBridge.php
 *
 * Implements legacy Covers interface by delegating calls to the modern Python Covers service.
 */

class CoversBridge
{
    private $python_bin = 'python3';
    private $bridge_script;
    
    public $cover_id = null;
    public $title = null;
    public $file = null;
    public $all_data = array();
    public $error = null;
    
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

    public function create($title, $file) {
        $resp = $this->call_bridge(array(
            'action' => 'covers',
            'method' => 'create',
            'title' => $title,
            'file' => $file
        ));

        if ($resp && !empty($resp['success'])) {
            $this->cover_id = $resp['cover_id'];
            $this->title = $title;
            $this->file = $file;
            $this->error = null;
            return true;
        }

        $this->error = isset($resp['error']) ? $resp['error'] : 'Cover page could not be created';
        return false;
    }

    public function delete_cover($id) {
        $resp = $this->call_bridge(array(
            'action' => 'covers',
            'method' => 'delete',
            'cover_id' => $id
        ));

        if ($resp && !empty($resp['success'])) {
            $this->error = null;
            return true;
        }

        $this->error = isset($resp['error']) ? $resp['error'] : 'Failed to delete cover';
        return false;
    }

    public function get_covers() {
        $resp = $this->call_bridge(array(
            'action' => 'covers',
            'method' => 'get_covers'
        ));

        if ($resp && isset($resp['covers']) && is_array($resp['covers'])) {
            $this->error = null;
            return $resp['covers'];
        }

        $this->error = isset($resp['error']) ? $resp['error'] : 'No cover pages configured';
        return null;
    }

    public function list_covers(&$title, &$file) {
        if ($this->cached_list === null) {
            $resp = $this->call_bridge(array(
                'action' => 'covers',
                'method' => 'list_all'
            ));
            $this->cached_list = ($resp && isset($resp['covers'])) ? $resp['covers'] : array();
            $this->list_index = 0;
        }

        if (isset($this->cached_list[$this->list_index])) {
            $item = $this->cached_list[$this->list_index++];
            $title = $item['title'];
            $file = $item['file'];
            return true;
        }

        $this->cached_list = null;
        $this->list_index = 0;
        $this->error = 'No cover pages configured';
        return false;
    }

    public function load_cover($file) {
        $resp = $this->call_bridge(array(
            'action' => 'covers',
            'method' => 'load',
            'file' => $file
        ));

        if ($resp && !empty($resp['success'])) {
            $this->cover_id = $resp['cover_id'];
            $this->title = $resp['title'];
            $this->file = $resp['file'];
            $this->all_data = isset($resp['all_data']) ? $resp['all_data'] : array();
            $this->error = null;
            return true;
        }

        $this->error = isset($resp['error']) ? $resp['error'] : "Cover page '$file' doesn't exist";
        return false;
    }

    public function get_cover_id() {
        return $this->cover_id;
    }

    public function get_title() {
        return $this->title;
    }

    public function get_file() {
        return $this->file;
    }

    public function set_title($title) {
        if (!$this->cover_id || !$this->file) {
            $this->error = 'No cover page loaded';
            return false;
        }

        $resp = $this->call_bridge(array(
            'action' => 'covers',
            'method' => 'set_title',
            'file' => $this->file,
            'title' => $title
        ));

        if ($resp && !empty($resp['success'])) {
            $this->title = $title;
            $this->all_data['title'] = $title;
            return true;
        }

        $this->error = isset($resp['error']) ? $resp['error'] : 'Failed to update title';
        return false;
    }

    public function set_file($file) {
        if (!$this->cover_id || !$this->file) {
            $this->error = 'No cover page loaded';
            return false;
        }

        $resp = $this->call_bridge(array(
            'action' => 'covers',
            'method' => 'set_file',
            'old_file' => $this->file,
            'new_file' => $file
        ));

        if ($resp && !empty($resp['success'])) {
            $this->file = $file;
            $this->all_data['file'] = $file;
            return true;
        }

        $this->error = isset($resp['error']) ? $resp['error'] : 'Failed to update file';
        return false;
    }
}
