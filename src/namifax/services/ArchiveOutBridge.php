<?php
/**
 * AvantFAX Modern Bridge: ArchiveOutBridge.php
 *
 * Implements legacy ArchiveOut interface by delegating calls to the modern Python ArchiveOut service.
 */

require_once 'FaxPDFArchiveBridge.php';

class ArchiveOut extends FaxPDFArchive
{
    private $python_bin = 'python3';
    private $bridge_script;

    public function __construct() {
        parent::__construct();
        $this->bridge_script = realpath(__DIR__ . '/../db/bridge_cli.py');
    }

    public function create($path, $userid, $cid, $origfaxnum, $pages) {
        global $INSTALLDIR;
        $req = array(
            'action' => 'archive_out',
            'method' => 'create',
            'installdir' => isset($INSTALLDIR) ? $INSTALLDIR : '',
            'path' => $path,
            'userid' => $userid,
            'cid' => $cid,
            'origfaxnum' => $origfaxnum,
            'pages' => $pages
        );

        $json_input = json_encode($req);
        $cmd = escapeshellcmd($this->python_bin) . ' ' . escapeshellarg($this->bridge_script) . ' ' . escapeshellarg($json_input);
        $output = shell_exec($cmd);
        if (!$output) return false;

        $resp = json_decode($output, true);
        if ($resp && !empty($resp['success'])) {
            $this->load_fax($resp['fid']);
            return true;
        }

        $this->error = isset($resp['error']) ? $resp['error'] : 'Failed to create archive_out entry';
        return false;
    }
}
