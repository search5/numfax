<?php
/**
 * AvantFAX Modern Bridge: FileUploadBridge.php
 *
 * Implements legacy FileUpload interface by delegating execution to modern Python upload handler.
 */

if (!defined('FU_NO_FILE'))     define('FU_NO_FILE',     201);
if (!defined('FU_INVALIDMIME')) define('FU_INVALIDMIME', 202);
if (!defined('FU_OVER_SIZE'))   define('FU_OVER_SIZE',   203);
if (!defined('FU_INI_SIZE'))    define('FU_INI_SIZE',    204);
if (!defined('FU_FORM_SIZE'))   define('FU_FORM_SIZE',   205);
if (!defined('FU_PARTIAL'))     define('FU_PARTIAL',     206);
if (!defined('FU_NO_TMPDIR'))   define('FU_NO_TMPDIR',   207);
if (!defined('FU_CANT_WRITE'))  define('FU_CANT_WRITE',  208);

class FileUploadBridge
{
    private $python_bin = 'python3';
    private $bridge_script;
    private $mimelimit = array();
    private $sizelimit = 0;
    private $file_info = null;
    private $filename = '';
    private $mimetype = '';
    private $filesize = 0;
    private $error = null;
    private $randname = false;
    private $randname_len = 9;
    public $debug = false;

    public function __construct() {
        $this->bridge_script = realpath(__DIR__ . '/../db/bridge_cli.py');
    }

    private function call_bridge($request) {
        $json_input = json_encode($request);
        $cmd = escapeshellcmd($this->python_bin) . ' ' . escapeshellarg($this->bridge_script) . ' ' . escapeshellarg($json_input);
        $output = shell_exec($cmd);
        if (!$output) return false;
        return json_decode($output, true);
    }

    public function limit_mimetype($array) {
        $this->mimelimit = is_array($array) ? $array : array($array);
        return true;
    }

    public function limit_size($size) {
        $this->sizelimit = $size;
        return true;
    }

    public function set_name($filename) {
        $resp = $this->call_bridge(array(
            'action' => 'upload_sanitize_filename',
            'filename' => $filename
        ));
        $this->filename = ($resp && isset($resp['clean'])) ? $resp['clean'] : basename($filename);
        return true;
    }

    public function set_randname($n = 9) {
        $this->randname = true;
        $this->randname_len = $n;
        return $this->filename;
    }

    public function load_file($file) {
        $this->file_info = $file;
        $resp = $this->call_bridge(array(
            'action' => 'upload_process',
            'file_info' => $file,
            'mimelimit' => $this->mimelimit,
            'sizelimit' => $this->sizelimit,
            'randname' => $this->randname,
            'randname_len' => $this->randname_len
        ));

        if ($resp && !empty($resp['success'])) {
            $this->filename = $resp['name'];
            $this->mimetype = $resp['mimetype'];
            $this->filesize = $resp['size'];
            return true;
        }

        $this->error = isset($resp['error']) ? $resp['error'] : FU_NO_FILE;
        return false;
    }

    public function get_name() {
        return $this->filename;
    }

    public function get_mimetype() {
        return $this->mimetype;
    }

    public function get_filesize() {
        return $this->filesize;
    }

    public function get_error() {
        return $this->error;
    }

    public function movefile($dir) {
        if (!$this->file_info) return false;

        $resp = $this->call_bridge(array(
            'action' => 'upload_process',
            'file_info' => $this->file_info,
            'mimelimit' => $this->mimelimit,
            'sizelimit' => $this->sizelimit,
            'dest_dir' => $dir,
            'randname' => $this->randname,
            'randname_len' => $this->randname_len
        ));

        return ($resp && !empty($resp['moved']));
    }
}
