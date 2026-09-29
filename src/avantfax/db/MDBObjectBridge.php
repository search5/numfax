<?php
/**
 * AvantFAX Modern Bridge: MDBObjectBridge.php
 *
 * Implements legacy MDBObject interface delegating entity CRUD to modern Python layer.
 */

require_once __DIR__ . '/MDBOBridge.php';

class MDBObjectBridge
{
    protected $table_id_name = 'id';
    protected $table_name = '';
    protected $db;
    public $debug = false;

    public function __construct() {
        if (empty($this->table_name)) {
            $this->table_name = get_class($this);
        }
        $this->db = new MDBOBridge($this);
    }

    public function get_table_name() {
        return $this->table_name;
    }

    public function get_table_id() {
        return $this->table_id_name;
    }

    public function get_db() {
        return $this->db;
    }

    public function get_id() {
        $id_col = $this->table_id_name;
        return isset($this->$id_col) ? $this->$id_col : null;
    }

    public function set_id($id) {
        if (!is_numeric($id)) return false;
        $id_col = $this->table_id_name;
        $this->$id_col = $id;
        return true;
    }

    public function set_vars(array $vals) {
        foreach ($vals as $key => $val) {
            $this->$key = $val;
        }
    }

    public function load($id) {
        $id_col = $this->table_id_name;
        $this->$id_col = $id;
        return $this->db->get($this);
    }

    public function delete() {
        return $this->db->delete($this);
    }
}
