<?php
/**
 * AvantFAX Modern Bridge: AFAddressBookBridge.php
 *
 * Implements legacy AFAddressBook interface by delegating calls to the modern Python AddressBookService.
 */

class AFAddressBookBridge
{
    private $python_bin = 'python3';
    private $bridge_script;

    protected $abook_id, $company;
    protected $email_array = array();
    protected $fax_array   = array();
    private   $error       = null;

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

    public function create($companyname) {
        $resp = $this->call_bridge(array(
            'action' => 'abook',
            'method' => 'create',
            'company' => $companyname
        ));

        if ($resp && !empty($resp['success'])) {
            $this->abook_id = $resp['abook_id'];
            $this->company = $companyname;
            $this->error = null;
            return true;
        }

        $this->error = isset($resp['error']) ? $resp['error'] : 'Company could not be created';
        return false;
    }

    public function loadbycid($cid) {
        $resp = $this->call_bridge(array(
            'action' => 'abook',
            'method' => 'loadbycid',
            'cid' => $cid
        ));

        if ($resp && !empty($resp['success'])) {
            $this->abook_id = $resp['abook_id'];
            $this->company = $resp['company'];
            $this->error = null;
            return true;
        }

        $this->abook_id = null;
        return false;
    }

    public function get_companies($with_reserved = false) {
        $resp = $this->call_bridge(array(
            'action' => 'abook',
            'method' => 'get_companies',
            'with_reserved' => $with_reserved
        ));

        return ($resp && isset($resp['companies'])) ? $resp['companies'] : array();
    }

    public function search_companies($query) {
        $resp = $this->call_bridge(array(
            'action' => 'abook',
            'method' => 'search_companies',
            'query' => $query
        ));

        return ($resp && isset($resp['companies'])) ? $resp['companies'] : array();
    }

    public function delete_cid($cid) {
        $resp = $this->call_bridge(array(
            'action' => 'abook',
            'method' => 'delete_cid',
            'cid' => $cid
        ));

        return ($resp && !empty($resp['success']));
    }

    public function create_faxnumid($faxnumber) {
        $resp = $this->call_bridge(array(
            'action' => 'abook',
            'method' => 'create_faxnumid',
            'cid' => $this->abook_id,
            'faxnumber' => $faxnumber
        ));

        if ($resp && !empty($resp['success'])) {
            $this->fax_array['abookfax_id'] = $resp['abookfax_id'];
            $this->fax_array['faxnumber'] = $faxnumber;
            return true;
        }

        return false;
    }

    public function loadbyfaxnum($faxnumber, &$mult) {
        $resp = $this->call_bridge(array(
            'action' => 'abook',
            'method' => 'loadbyfaxnum',
            'faxnumber' => $faxnumber
        ));

        $mult = ($resp && !empty($resp['multiple']));
        if ($resp && !empty($resp['success'])) {
            $this->fax_array['abookfax_id'] = $resp['abookfax_id'];
            $this->company = $resp['company'];
            return true;
        }

        return false;
    }

    public function loadbyfaxnumid($abookfax_id) {
        $resp = $this->call_bridge(array(
            'action' => 'abook',
            'method' => 'loadbyfaxnumid',
            'abookfax_id' => $abookfax_id
        ));

        if ($resp && !empty($resp['success'])) {
            $this->fax_array['abookfax_id'] = $resp['abookfax_id'];
            $this->fax_array['faxnumber'] = $resp['faxnumber'];
            $this->company = $resp['company'];
            return true;
        }

        return false;
    }

    public function create_contact($name, $email) {
        $resp = $this->call_bridge(array(
            'action' => 'abook',
            'method' => 'create_contact',
            'cid' => $this->abook_id,
            'name' => $name,
            'email' => $email
        ));

        return ($resp && !empty($resp['success']));
    }

    public function get_contacts() {
        $resp = $this->call_bridge(array(
            'action' => 'abook',
            'method' => 'get_contacts'
        ));

        return ($resp && isset($resp['contacts'])) ? $resp['contacts'] : array();
    }

    public function remove_contact($abookemail_id) {
        $resp = $this->call_bridge(array(
            'action' => 'abook',
            'method' => 'remove_contact',
            'abookemail_id' => $abookemail_id
        ));

        return ($resp && !empty($resp['success']));
    }

    public function get_companyid()    { return $this->abook_id; }
    public function get_company()      { return $this->company; }
    public function get_faxnumber()    { return isset($this->fax_array['faxnumber']) ? $this->fax_array['faxnumber'] : null; }
    public function get_faxnumid()     { return isset($this->fax_array['abookfax_id']) ? $this->fax_array['abookfax_id'] : null; }
    public function get_error()        { return $this->error; }
}
