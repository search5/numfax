<?php
/**
 * AvantFAX Modern Bridge: MDBOBridge.php
 *
 * Implements legacy MDBO interface by delegating calls to the modern Python QueryBuilder.
 */

if (!defined('SQL_AND')) define('SQL_AND', ' AND ');
if (!defined('SQL_OR'))  define('SQL_OR',  ' OR ');

class MDBOBridge
{
    private $python_bin = 'python3';
    private $bridge_script;
    private $dbobject;
    private $num_results = 0;
    public $debug = false;

    public function __construct($dbobject = null) {
        $this->bridge_script = realpath(__DIR__ . '/bridge_cli.py');
        $this->dbobject = $dbobject;
    }

    private function call_bridge($request) {
        $json_input = json_encode($request);
        $cmd = escapeshellcmd($this->python_bin) . ' ' . escapeshellarg($this->bridge_script) . ' ' . escapeshellarg($json_input);
        $output = shell_exec($cmd);
        if (!$output) return false;
        return json_decode($output, true);
    }

    public function insert($dbobject) {
        $table = method_exists($dbobject, 'get_table_name') ? $dbobject->get_table_name() : get_class($dbobject);
        $id_col = method_exists($dbobject, 'get_table_id') ? $dbobject->get_table_id() : null;
        $data = get_object_vars($dbobject);

        $resp = $this->call_bridge(array(
            'action' => 'insert',
            'table' => $table,
            'id_col' => $id_col,
            'data' => $data
        ));

        if ($resp && !empty($resp['insert_id'])) {
            if (method_exists($dbobject, 'set_id')) {
                $dbobject->set_id($resp['insert_id']);
            }
            return true;
        }
        return false;
    }

    public function update($dbobject) {
        $table = method_exists($dbobject, 'get_table_name') ? $dbobject->get_table_name() : get_class($dbobject);
        $id_col = method_exists($dbobject, 'get_table_id') ? $dbobject->get_table_id() : 'id';
        $id_val = method_exists($dbobject, 'get_id') ? $dbobject->get_id() : null;
        $data = get_object_vars($dbobject);

        $resp = $this->call_bridge(array(
            'action' => 'update',
            'table' => $table,
            'data' => $data,
            'where' => array($id_col => $id_val)
        ));

        return ($resp && !empty($resp['success']));
    }

    public function get($dbobject) {
        $table = method_exists($dbobject, 'get_table_name') ? $dbobject->get_table_name() : get_class($dbobject);
        $id_col = method_exists($dbobject, 'get_table_id') ? $dbobject->get_table_id() : 'id';
        $id_val = method_exists($dbobject, 'get_id') ? $dbobject->get_id() : null;

        $resp = $this->call_bridge(array(
            'action' => 'get',
            'table' => $table,
            'id_col' => $id_col,
            'id_val' => $id_val
        ));

        if ($resp && !empty($resp['record'])) {
            if (method_exists($dbobject, 'set_vars')) {
                $dbobject->set_vars($resp['record']);
            }
            return true;
        }
        return false;
    }

    public function find($dbobject, $query_logic = SQL_AND, $limit = null, $offset = null, $include_index = false, $reduce_array = true) {
        $table = method_exists($dbobject, 'get_table_name') ? $dbobject->get_table_name() : get_class($dbobject);
        $data = get_object_vars($dbobject);

        $conditions = array();
        foreach ($data as $k => $v) {
            if ($v !== null && $v !== '') {
                $conditions[$k] = $v;
            }
        }

        $resp = $this->call_bridge(array(
            'action' => 'find',
            'table' => $table,
            'conditions' => $conditions,
            'logic' => $query_logic,
            'limit' => $limit,
            'offset' => $offset,
            'reduce_single' => $reduce_array
        ));

        if ($resp && isset($resp['records'])) {
            $this->num_results = isset($resp['num_results']) ? $resp['num_results'] : 0;
            return $resp['records'];
        }
        return null;
    }

    public function delete($dbobject) {
        $table = method_exists($dbobject, 'get_table_name') ? $dbobject->get_table_name() : get_class($dbobject);
        $id_col = method_exists($dbobject, 'get_table_id') ? $dbobject->get_table_id() : 'id';
        $id_val = method_exists($dbobject, 'get_id') ? $dbobject->get_id() : null;

        $resp = $this->call_bridge(array(
            'action' => 'delete',
            'table' => $table,
            'id_col' => $id_col,
            'id_val' => $id_val
        ));

        return ($resp && !empty($resp['success']));
    }

    public function get_num_results() {
        return $this->num_results;
    }
}
