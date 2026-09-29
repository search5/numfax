<?php
/**
 * AvantFAX Modern Bridge: SQLBridge.php
 *
 * Implements legacy SQL interface by delegating calls to the modern Python DatabaseEngine.
 */

define('SQL_NONE', 1);
define('SQL_ALL', 2);

class SQLBridge
{
    private $python_bin = 'python3';
    private $bridge_script;
    private $connected = false;
    private $record = array();
    private $records = array();
    private $current_index = 0;
    private $last_query = '';
    private $last_insert_id = null;
    private $error = null;
    public $debug = false;

    public function __construct() {
        $this->bridge_script = realpath(__DIR__ . '/bridge_cli.py');
    }

    private function call_bridge($request) {
        $json_input = json_encode($request);
        $cmd = escapeshellcmd($this->python_bin) . ' ' . escapeshellarg($this->bridge_script) . ' ' . escapeshellarg($json_input);
        $output = shell_exec($cmd);
        if (!$output) {
            $this->error = "Bridge execution failed";
            return false;
        }
        return json_decode($output, true);
    }

    public function connect($db_user, $db_pass, $db_name, $db_host, $db_engine = 'sqlite') {
        $resp = $this->call_bridge(array(
            'action' => 'connect',
            'engine' => $db_engine,
            'user' => $db_user,
            'password' => $db_pass,
            'database' => $db_name,
            'host' => $db_host
        ));

        if ($resp && !empty($resp['success'])) {
            $this->connected = true;
            return true;
        }
        $this->error = isset($resp['error']) ? $resp['error'] : 'Unknown connect error';
        return false;
    }

    public function disconnect() {
        $this->connected = false;
    }

    public function query($query, &$num = 0, $type = SQL_NONE) {
        $this->last_query = $query;
        $this->record = array();
        $this->records = array();
        $this->current_index = 0;

        $resp = $this->call_bridge(array(
            'action' => 'query',
            'sql' => $query,
            'fetch_all' => ($type === SQL_ALL)
        ));

        if (!$resp || empty($resp['executed'])) {
            $this->error = isset($resp['error']) ? $resp['error'] : 'Query failed';
            return false;
        }

        $this->records = isset($resp['records']) ? $resp['records'] : array();
        $this->last_insert_id = isset($resp['insert_id']) ? $resp['insert_id'] : null;

        if (preg_match("/^SELECT/i", $query)) {
            $num = isset($resp['row_count']) ? $resp['row_count'] : count($this->records);
        } else {
            $num = isset($resp['affected_rows']) ? $resp['affected_rows'] : 0;
        }

        return true;
    }

    public function getRecords() {
        return $this->records;
    }

    public function getResult() {
        if ($this->current_index < count($this->records)) {
            $row = $this->records[$this->current_index];
            $this->current_index++;
            return $row;
        }
        return false;
    }

    public function getInsertID() {
        return $this->last_insert_id;
    }

    public function getError() {
        return $this->error;
    }

    public function getLastQuery() {
        return $this->last_query;
    }

    public function quote($string) {
        $resp = $this->call_bridge(array(
            'action' => 'quote',
            'value' => $string
        ));
        return isset($resp['quoted']) ? $resp['quoted'] : "'" . addslashes($string) . "'";
    }

    public function genXML($xmlTitle = true, $mysqlStyle = "response", $metaHeader = "row", $htmlEntities = true) {
        $resp = $this->call_bridge(array(
            'action' => 'xml',
            'xml_title' => $xmlTitle,
            'mysql_style' => $mysqlStyle,
            'root_tag' => ($mysqlStyle === false) ? 'response' : $mysqlStyle,
            'row_tag' => $metaHeader
        ));
        return isset($resp['xml']) ? $resp['xml'] : '<noelement></noelement>';
    }
}
