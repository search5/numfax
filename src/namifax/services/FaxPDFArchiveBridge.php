<?php
/**
 * AvantFAX Modern Bridge: FaxPDFArchiveBridge.php
 *
 * Implements legacy FaxPDFArchive interface by delegating calls to the modern Python FaxPDFArchive service.
 */

class FaxPDFArchive
{
    private $python_bin = 'python3';
    private $bridge_script;

    protected $thumbnail       = NULL,
              $tiffpath        = NULL,
              $pdfpath         = NULL,
              $faximages       = NULL,
              $m_archstamp     = NULL,
              $m_lastmoddate   = NULL,
              $m_lastoperation = NULL,
              $error           = NULL;

    protected $dbdata = array();
    private   $archive_results = NULL;

    public function __construct() {
        $this->bridge_script = realpath(__DIR__ . '/../db/bridge_cli.py');
    }

    private function call_bridge(array $req) {
        global $INSTALLDIR;
        $req['installdir'] = isset($INSTALLDIR) ? $INSTALLDIR : '';
        if (isset($this->dbdata['fid']) && !isset($req['fid'])) {
            $req['fid'] = $this->dbdata['fid'];
        }
        $json_input = json_encode($req);
        $cmd = escapeshellcmd($this->python_bin) . ' ' . escapeshellarg($this->bridge_script) . ' ' . escapeshellarg($json_input);
        $output = shell_exec($cmd);
        if (!$output) return false;
        return json_decode($output, true);
    }

    public function get_faxcatid() {
        if (!array_key_exists('fid', $this->dbdata)) { $this->error = "No fid loaded"; return false; }
        return $this->dbdata['faxcatid'];
    }

    public function get_num_faxes($devices, $faxcats) {
        global $ENABLE_DID_ROUTING;
        $resp = $this->call_bridge(array(
            'action' => 'archive_base',
            'method' => 'get_num_faxes',
            'devices' => $devices,
            'faxcats' => $faxcats,
            'enable_did_routing' => !empty($ENABLE_DID_ROUTING)
        ));
        return ($resp && isset($resp['count'])) ? $resp['count'] : 0;
    }

    public function get_error() { return $this->error; }

    public function user_has_rights($userid, array $modems, array $routes, array $faxcat) {
        if (!array_key_exists('fid', $this->dbdata)) { $this->error = "No fid loaded"; return false; }
        $resp = $this->call_bridge(array(
            'action' => 'archive_base',
            'method' => 'user_has_rights',
            'userid' => $userid,
            'modems' => $modems,
            'routes' => $routes,
            'faxcat' => $faxcat
        ));
        return !empty($resp['has_rights']);
    }

    public function check_empty_array(array $a) {
        $cnt = count($a);
        if ($cnt > 0) {
            if ($a[0] == NULL) {
                array_shift($a);
            }
        }
        return $a;
    }

    public function get_fid_prev() {
        if (!array_key_exists('fid', $this->dbdata)) { $this->error = "No fid loaded"; return false; }
        $resp = $this->call_bridge(array(
            'action' => 'archive_base',
            'method' => 'get_fid_prev'
        ));
        return ($resp && isset($resp['fid'])) ? $resp['fid'] : NULL;
    }

    public function get_fid_next() {
        if (!array_key_exists('fid', $this->dbdata)) { $this->error = "No fid loaded"; return false; }
        $resp = $this->call_bridge(array(
            'action' => 'archive_base',
            'method' => 'get_fid_next'
        ));
        return ($resp && isset($resp['fid'])) ? $resp['fid'] : NULL;
    }

    public function search_archive($criteria) {
        global $ENABLE_DID_ROUTING;
        $criteria['enable_did_routing'] = !empty($ENABLE_DID_ROUTING);
        if (defined('RESTRICTED_USER_MODE')) {
            $criteria['restricted_user_mode'] = RESTRICTED_USER_MODE;
        }

        $resp = $this->call_bridge(array(
            'action' => 'archive_base',
            'method' => 'search_archive',
            'criteria' => $criteria
        ));

        if ($resp && isset($resp['total'])) {
            $this->archive_results = $resp['entries'];
            return $resp['total'];
        }
        return 0;
    }

    public function next_archive_entry(&$fid) {
        if (is_array($this->archive_results)) {
            if ($data = array_shift($this->archive_results)) {
                $fid = $data;
                return true;
            }
        }
        $this->archive_results = NULL;
        return false;
    }

    public function viewable_devices($devices, $faxcats) {
        // Handled automatically within python calls
    }

    public function list_inbox($devices, $index = 0, $limit = 25, $faxcats = null) {
        static $results;
        global $ENABLE_DID_ROUTING;

        if ($results === null) {
            $resp = $this->call_bridge(array(
                'action' => 'archive_base',
                'method' => 'list_inbox',
                'devices' => $devices,
                'index' => $index,
                'limit' => $limit,
                'faxcats' => $faxcats,
                'enable_did_routing' => !empty($ENABLE_DID_ROUTING),
                'order_by_modem' => defined('INBOX_LIST_MODEM') ? INBOX_LIST_MODEM : false
            ));
            $results = ($resp && isset($resp['items'])) ? $resp['items'] : array();
        }

        if (is_array($results) && count($results) > 0) {
            $data = array_shift($results);
            $this->load_vals($data);
            return true;
        }

        $results = null;
        return false;
    }

    public function load_fax($faxid) {
        $resp = $this->call_bridge(array(
            'action' => 'archive_base',
            'method' => 'load_fax',
            'faxid' => $faxid
        ));

        if ($resp && !empty($resp['success'])) {
            $this->load_vals($resp['data']);
            $this->error = null;
            return true;
        }

        $this->error = isset($resp['error']) ? $resp['error'] : "load_fax error: $faxid didn't load";
        return false;
    }

    public function set_category($catid, $userid = 0) {
        if (!array_key_exists('fid', $this->dbdata)) { $this->error = "No fid loaded"; return false; }
        $resp = $this->call_bridge(array(
            'action' => 'archive_base',
            'method' => 'set_category',
            'catid' => $catid,
            'userid' => $userid
        ));
        if ($resp && !empty($resp['success'])) {
            $this->dbdata['faxcatid'] = $catid;
            $this->dbdata['lastmoduser'] = $userid;
            return true;
        }
        return false;
    }

    public function remove_category($catid) {
        $resp = $this->call_bridge(array(
            'action' => 'archive_base',
            'method' => 'remove_category',
            'catid' => $catid
        ));
        return ($resp && !empty($resp['success']));
    }

    public function set_note($description, $category, $userid) {
        if (!array_key_exists('fid', $this->dbdata)) { $this->error = "No fid loaded"; return false; }
        $resp = $this->call_bridge(array(
            'action' => 'archive_base',
            'method' => 'set_note',
            'description' => $description,
            'category' => $category,
            'userid' => $userid
        ));
        if ($resp && !empty($resp['success'])) {
            $this->dbdata['faxcatid'] = $category;
            $this->dbdata['description'] = $description;
            $this->dbdata['lastmoduser'] = $userid;
            return true;
        }
        return false;
    }

    public function set_faxcontent($faxcontent) {
        if (!array_key_exists('fid', $this->dbdata)) { $this->error = "No fid loaded"; return false; }
        $resp = $this->call_bridge(array(
            'action' => 'archive_base',
            'method' => 'set_faxcontent',
            'faxcontent' => $faxcontent
        ));
        if ($resp && !empty($resp['success'])) {
            $this->dbdata['faxcontent'] = $faxcontent;
            return true;
        }
        return false;
    }

    public function delete_fax($fid = NULL) {
        $target_fid = $fid ? $fid : (isset($this->dbdata['fid']) ? $this->dbdata['fid'] : NULL);
        if (!$target_fid) { $this->error = "No fid loaded"; return false; }

        $resp = $this->call_bridge(array(
            'action' => 'archive_base',
            'method' => 'delete_fax',
            'fid' => $target_fid
        ));
        return ($resp && !empty($resp['success']));
    }

    public function prune_archive($days) {
        $resp = $this->call_bridge(array(
            'action' => 'archive_base',
            'method' => 'prune_archive',
            'days' => $days
        ));
        return ($resp && isset($resp['pruned'])) ? $resp['pruned'] : 0;
    }

    public function set_faxnumid($id) {
        if (!array_key_exists('fid', $this->dbdata)) { $this->error = "No fid loaded"; return false; }
        $resp = $this->call_bridge(array(
            'action' => 'archive_base',
            'method' => 'set_faxnumid',
            'id' => $id
        ));
        if ($resp && !empty($resp['success'])) {
            $this->dbdata['faxnumid'] = $id;
            return true;
        }
        $this->error = "faxnumid not updated";
        return false;
    }

    public function set_companyid($id) {
        if (!array_key_exists('fid', $this->dbdata)) { $this->error = "No fid loaded"; return false; }
        $resp = $this->call_bridge(array(
            'action' => 'archive_base',
            'method' => 'set_companyid',
            'id' => $id
        ));
        if ($resp && !empty($resp['success'])) {
            $this->dbdata['companyid'] = $id;
            return true;
        }
        $this->error = "companyid not updated";
        return false;
    }

    public function reassign($oldcid, $newcid) {
        $resp = $this->call_bridge(array(
            'action' => 'archive_base',
            'method' => 'reassign',
            'oldcid' => $oldcid,
            'newcid' => $newcid
        ));
        return ($resp && !empty($resp['success']));
    }

    public function get_userid()        { return isset($this->dbdata['userid']) ? $this->dbdata['userid'] : NULL; }
    public function get_fid()           { return isset($this->dbdata['fid']) ? $this->dbdata['fid'] : NULL; }
    public function get_description()   { return isset($this->dbdata['description']) ? $this->dbdata['description'] : NULL; }
    public function get_lastmoduser()   { return isset($this->dbdata['lastmoduser']) ? $this->dbdata['lastmoduser'] : NULL; }
    public function get_faxnumid()      { return isset($this->dbdata['faxnumid']) ? $this->dbdata['faxnumid'] : NULL; }
    public function get_origfaxnum()    { return isset($this->dbdata['origfaxnum']) ? $this->dbdata['origfaxnum'] : NULL; }
    public function get_pages()         { return isset($this->dbdata['pages']) ? $this->dbdata['pages'] : NULL; }
    public function get_inbox()         { return isset($this->dbdata['inbox']) ? $this->dbdata['inbox'] : NULL; }
    public function get_companyid()     { return isset($this->dbdata['companyid']) ? $this->dbdata['companyid'] : NULL; }
    public function get_didr_id()       { return isset($this->dbdata['didr_id']) ? $this->dbdata['didr_id'] : NULL; }
    public function get_modemdev()      { return isset($this->dbdata['modemdev']) ? $this->dbdata['modemdev'] : NULL; }
    public function get_tiffpath()      { return $this->tiffpath; }
    public function get_pdfpath()       { return $this->pdfpath; }
    public function get_thumbnail()     { return $this->thumbnail; }
    public function get_faximages()     { return $this->faximages; }
    public function get_archstamp()     { return $this->m_archstamp; }
    public function get_lastmoddate()   { return $this->m_lastmoddate; }

    protected function create_fax($path, $faxnid, $faxnumber, $pages, $date = NULL, $didr_id = NULL) {
        $resp = $this->call_bridge(array(
            'action' => 'archive_base',
            'method' => 'create_fax',
            'path' => $path,
            'faxnid' => $faxnid,
            'faxnumber' => $faxnumber,
            'pages' => $pages,
            'date' => $date,
            'didr_id' => $didr_id
        ));

        if ($resp && !empty($resp['success'])) {
            $this->load_fax($resp['fid']);
            return true;
        }

        $this->error = isset($resp['error']) ? $resp['error'] : "No id created";
        return false;
    }

    private function load_vals(array $data) {
        $this->m_archstamp = isset($data['m_archstamp']) ? $data['m_archstamp'] : null;
        $this->m_lastmoddate = isset($data['m_lastmoddate']) ? $data['m_lastmoddate'] : null;
        $this->m_lastoperation = isset($data['m_lastoperation']) ? $data['m_lastoperation'] : null;

        unset($data['m_archstamp'], $data['m_lastmoddate'], $data['m_lastoperation']);
        $this->dbdata = $data;

        $faxpath = isset($this->dbdata['faxpath']) ? $this->dbdata['faxpath'] : '';
        $this->pdfpath = $faxpath . DIRECTORY_SEPARATOR . 'fax.pdf';
        $this->thumbnail = $faxpath . DIRECTORY_SEPARATOR . 'thumb.png';
        $this->tiffpath = $faxpath . DIRECTORY_SEPARATOR . 'fax.tif';

        $this->faximages = array();
        $pages = isset($this->dbdata['pages']) ? (int)$this->dbdata['pages'] : 0;
        for ($i = 0; $i < $pages; $i++) {
            $this->faximages[$i] = $faxpath . DIRECTORY_SEPARATOR . 'page' . $i . '.png';
        }
    }
}
