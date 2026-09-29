<?php
/**
 * AvantFAX Modern Bridge: MailerBridge.php
 *
 * Implements legacy Mailer interface by delegating email dispatch to modern Python MailerService.
 */

class MailerBridge
{
    private $python_bin = 'python3';
    private $bridge_script;
    private $subject = 'AvantFAX Notification';
    private $text = '';
    private $attachments = array();
    private $images = array();
    private $error = null;
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

    public function setMessage($text) {
        $this->text = $text;
    }

    public function setSubject($subject) {
        $this->subject = $subject;
    }

    public function attachFile($file, $altname = null) {
        if ($file && file_exists($file)) {
            $this->attachments[] = array('file' => realpath($file), 'altname' => $altname);
        }
    }

    public function embeddImage($image) {
        if ($image && file_exists($image)) {
            $this->images[] = array('file' => realpath($image), 'cid' => basename($image));
        }
    }

    public function sendmail($to) {
        $resp = $this->call_bridge(array(
            'action' => 'mailer_send',
            'to' => $to,
            'subject' => $this->subject,
            'text' => $this->text,
            'attachments' => $this->attachments,
            'images' => $this->images,
            'spool_mode' => true // safe default for bridge
        ));

        if ($resp && !empty($resp['success'])) {
            return true;
        }

        $this->error = isset($resp['error']) ? $resp['error'] : 'Send failed';
        return false;
    }

    public function getError() {
        return $this->error;
    }
}
