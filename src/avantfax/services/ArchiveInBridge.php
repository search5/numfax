<?php
/**
 * AvantFAX Modern Bridge: ArchiveInBridge.php
 *
 * Implements legacy ArchiveIn interface by delegating calls to the modern Python ArchiveIn service.
 */

require_once 'FaxPDFArchiveBridge.php';

class ArchiveIn extends FaxPDFArchive
{
    private $python_bin = 'python3';
    private $bridge_script;

    public function __construct() {
        parent::__construct();
        $this->bridge_script = realpath(__DIR__ . '/../db/bridge_cli.py');
    }

    private function call_in_bridge(array $req) {
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

    public function create($path, $faxnid, $faxnumber, $modem, $pages, $date = NULL, $didr_id = NULL) {
        $resp = $this->call_in_bridge(array(
            'action' => 'archive_in',
            'method' => 'create',
            'path' => $path,
            'faxnid' => $faxnid,
            'faxnumber' => $faxnumber,
            'modem' => $modem,
            'pages' => $pages,
            'date' => $date,
            'didr_id' => $didr_id
        ));

        if ($resp && !empty($resp['success'])) {
            $this->load_fax($resp['fid']);
            return true;
        }

        $this->error = isset($resp['error']) ? $resp['error'] : 'Failed to create archive_in entry';
        return false;
    }

    public function set_archivebox($faxid) {
        $resp = $this->call_in_bridge(array(
            'action' => 'archive_in',
            'method' => 'set_archivebox',
            'faxid' => $faxid
        ));

        if ($resp && !empty($resp['success'])) {
            $this->dbdata['inbox'] = false;
            return true;
        }

        $this->error = isset($resp['error']) ? $resp['error'] : 'Failed to set archivebox';
        return false;
    }

    public function rotate_fax() {
        if (!array_key_exists('fid', $this->dbdata)) { $this->error = "No fid loaded"; return false; }
        if (!$this->dbdata['inbox']) { $this->error = "Not in inbox"; return false; }

        $resp = $this->call_in_bridge(array(
            'action' => 'archive_in',
            'method' => 'rotate_fax',
            'fid' => $this->dbdata['fid']
        ));

        if ($resp && !empty($resp['success'])) {
            return true;
        }

        $this->error = isset($resp['error']) ? $resp['error'] : 'Failed to rotate fax';
        return false;
    }

    public function prune_inbox($days) {
        $resp = $this->call_in_bridge(array(
            'action' => 'archive_in',
            'method' => 'prune_inbox',
            'days' => $days
        ));
        return ($resp && isset($resp['count'])) ? $resp['count'] : 0;
    }
}
