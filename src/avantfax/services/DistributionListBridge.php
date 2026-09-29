<?php
/**
 * AvantFAX Modern Bridge: DistributionListBridge.php
 *
 * Implements legacy DistributionList interface by delegating calls to the modern Python DistributionListService.
 */

if (!defined('DL_SEPARATOR')) {
    define('DL_SEPARATOR', ':');
}

class DistributionListBridge
{
    private $python_bin = 'python3';
    private $bridge_script;

    private $dl_id        = null;
    private $error        = null;
    private $listname     = null;
    private $listdata     = null;
    private $lastmod_date = null;
    private $lastmod_user = null;

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

    public function get_dl_id() {
        return $this->dl_id;
    }

    public function get_listname() {
        return $this->listname;
    }

    public function get_lastmod() {
        return array('date' => $this->lastmod_date, 'user' => $this->lastmod_user);
    }

    public function get_error() {
        return $this->error;
    }

    public function set_moduser($moduser) {
        $this->lastmod_user = $moduser;
    }

    public function create($listname) {
        $resp = $this->call_bridge(array(
            'action' => 'distro',
            'method' => 'create',
            'listname' => $listname,
            'user' => $this->lastmod_user
        ));

        if ($resp && !empty($resp['success'])) {
            $this->dl_id = $resp['dl_id'];
            $this->listname = $listname;
            $this->error = null;
            return true;
        }

        $this->error = isset($resp['error']) ? $resp['error'] : 'Distribution list could not be created';
        return false;
    }

    public function delete_list($list_id) {
        $resp = $this->call_bridge(array(
            'action' => 'distro',
            'method' => 'delete',
            'list_id' => $list_id
        ));

        return ($resp && !empty($resp['success']));
    }

    public function get_distrolists() {
        $resp = $this->call_bridge(array(
            'action' => 'distro',
            'method' => 'get_distrolists'
        ));

        if ($resp && isset($resp['lists']) && is_array($resp['lists'])) {
            return $resp['lists'];
        }
        return array();
    }

    public function load_list($id) {
        if (!$id) {
            $this->error = 'DList not selected';
            return false;
        }

        $resp = $this->call_bridge(array(
            'action' => 'distro',
            'method' => 'load',
            'list_id' => $id
        ));

        if ($resp && !empty($resp['success'])) {
            $this->dl_id = $resp['dl_id'];
            $this->listname = $resp['listname'];
            $lastmod = isset($resp['lastmod']) ? $resp['lastmod'] : array();
            $this->lastmod_date = isset($lastmod['date']) ? $lastmod['date'] : null;
            $this->lastmod_user = isset($lastmod['user']) ? $lastmod['user'] : null;
            $entries = isset($resp['entries']) ? $resp['entries'] : array();
            $this->listdata = implode(DL_SEPARATOR, $entries);
            $this->error = null;
            return true;
        }

        $this->error = isset($resp['error']) ? $resp['error'] : "List $id doesn't exist.";
        return false;
    }

    public function set_listname($listname) {
        if (!$this->dl_id) {
            $this->error = 'No list loaded';
            return false;
        }

        $resp = $this->call_bridge(array(
            'action' => 'distro',
            'method' => 'set_listname',
            'list_id' => $this->dl_id,
            'listname' => $listname,
            'user' => $this->lastmod_user
        ));

        if ($resp && !empty($resp['success'])) {
            $this->listname = $listname;
            $this->error = null;
            return true;
        }

        $this->error = isset($resp['error']) ? $resp['error'] : 'Failed to update listname';
        return false;
    }

    public function list_entries() {
        if (!$this->dl_id) {
            $this->error = 'No list loaded';
            return false;
        }

        $resp = $this->call_bridge(array(
            'action' => 'distro',
            'method' => 'list_entries',
            'list_id' => $this->dl_id
        ));

        if ($resp && isset($resp['entries']) && is_array($resp['entries'])) {
            return $resp['entries'];
        }
        return array();
    }

    public function add_entries($entries) {
        if (!$this->dl_id) {
            $this->error = 'No list loaded';
            return false;
        }

        if (!is_array($entries)) return false;

        $resp = $this->call_bridge(array(
            'action' => 'distro',
            'method' => 'add_entries',
            'list_id' => $this->dl_id,
            'entries' => $entries,
            'user' => $this->lastmod_user
        ));

        if ($resp && !empty($resp['success'])) {
            $this->error = null;
            return true;
        }

        return false;
    }

    public function remove_entries($entries) {
        if (!$this->dl_id) {
            $this->error = 'No list loaded';
            return false;
        }

        if (!is_array($entries)) return false;

        $resp = $this->call_bridge(array(
            'action' => 'distro',
            'method' => 'remove_entries',
            'list_id' => $this->dl_id,
            'entries' => $entries,
            'user' => $this->lastmod_user
        ));

        if ($resp && !empty($resp['success'])) {
            $this->error = null;
            return true;
        }

        return false;
    }
}
