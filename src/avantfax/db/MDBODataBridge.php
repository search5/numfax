<?php
/**
 * AvantFAX Modern Bridge: MDBODataBridge.php
 *
 * Implements legacy MDBOData interface utilizing modern MDBOBridge and entities.
 */

require_once __DIR__ . '/MDBOBridge.php';
require_once __DIR__ . '/../models/EntitiesBridge.php';

class MDBODataBridge
{
    public $data;
    protected $dbo;
    public $debug = false;

    public function __construct($classType) {
        $bridgeClass = $classType . 'Bridge';
        if (class_exists($bridgeClass)) {
            $this->data = new $bridgeClass;
        } elseif (class_exists($classType)) {
            $this->data = new $classType;
        } else {
            $this->data = new MDBObjectBridge;
        }
        $this->dbo = new MDBOBridge($this->data);
    }

    public function load($id) {
        return $this->data->load($id);
    }

    public function new_entry(array $info) {
        $this->data->set_vars($info);
        return $this->dbo->insert($this->data);
    }

    public function update_entry(array $info = null) {
        if (is_array($info)) {
            $this->data->set_vars($info);
        }
        return $this->dbo->update($this->data);
    }

    public function delete_entry(array $info = null) {
        if (is_array($info)) {
            $this->data->set_vars($info);
        }
        return $this->dbo->delete($this->data);
    }

    public function get_info() {
        return get_object_vars($this->data);
    }

    public function get_id() {
        return $this->data->get_id();
    }

    public function find(array $info, $query_logic = SQL_AND, $limit = null, $offset = null, $include_index = false, $reduce_array = true) {
        $this->data->set_vars($info);
        return $this->dbo->find($this->data, $query_logic, $limit, $offset, $include_index, $reduce_array);
    }

    public function findext(array $info) {
        return $this->find($info, SQL_AND, null, null, true);
    }

    public function query($query, $reduce_array = true) {
        // delegate arbitrary query
        return null;
    }

    public function get_error() {
        return null;
    }
}
