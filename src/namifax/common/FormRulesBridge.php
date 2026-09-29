<?php
/**
 * AvantFAX Modern Bridge: FormRulesBridge.php
 *
 * Implements legacy FormRules interface by delegating validation to modern Python validators.
 */

if (!defined('FR_ARRAY'))  define('FR_ARRAY',  10);
if (!defined('FR_STRING')) define('FR_STRING', 11);
if (!defined('FR_NUMBER')) define('FR_NUMBER', 12);
if (!defined('FR_DATE'))   define('FR_DATE',   13);
if (!defined('FR_EMAIL'))  define('FR_EMAIL',  14);

class FormRulesBridge
{
    private $python_bin = 'python3';
    private $bridge_script;
    private $rules = array();
    private $errors = array();
    private $form_errors = array();
    private $css_errors = null;
    private $html_ready_vals = array();
    private $db_ready_vals = array();
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

    public function newRule($varname, $defaultval = null, $vartype = FR_STRING, $minlen = null, $maxlen = null, $error_str = null, $required = false, $sanitize = true, $execfunc = null) {
        if (!$varname) {
            $this->errors[] = "Must set variable name";
            return false;
        }

        $this->rules[$varname] = array(
            'varname' => $varname,
            'defaultval' => $defaultval,
            'vartype' => $vartype,
            'minlen' => $minlen,
            'maxlen' => $maxlen,
            'error_str' => $error_str,
            'required' => $required,
            'sanitize' => $sanitize
        );
        return true;
    }

    public function processForm(array $post) {
        $resp = $this->call_bridge(array(
            'action' => 'validate_form',
            'rules' => array_values($this->rules),
            'data' => $post
        ));

        if ($resp) {
            $this->form_errors = isset($resp['errors']) ? $resp['errors'] : array();
            $this->css_errors = isset($resp['css_errors']) ? $resp['css_errors'] : null;
            $this->html_ready_vals = isset($resp['html_ready']) ? $resp['html_ready'] : array();
            $this->db_ready_vals = isset($resp['db_ready']) ? $resp['db_ready'] : array();
            return !empty($resp['valid']);
        }
        return false;
    }

    public function getFormErrors() {
        return $this->form_errors;
    }

    public function getErrors() {
        return $this->errors;
    }

    public function getCSSErrorIDs() {
        return $this->css_errors;
    }

    public function htmlReady() {
        return $this->html_ready_vals;
    }

    public function dbReady() {
        return $this->db_ready_vals;
    }
}
