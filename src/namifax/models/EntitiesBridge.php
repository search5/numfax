<?php
/**
 * AvantFAX Modern Bridge: EntitiesBridge.php
 *
 * Implements legacy classes.php database extraction classes by extending MDBObjectBridge.
 */

require_once __DIR__ . '/../db/MDBObjectBridge.php';

class DistroListBridge extends MDBObjectBridge {
    protected $table_id_name = 'dl_id';
    protected $table_name = 'DistroList';
    public $dl_id, $listname, $listdata, $lastmod_date, $lastmod_user;
}

class UserAccountBridge extends MDBObjectBridge {
    protected $table_id_name = 'uid';
    protected $table_name = 'UserAccount';
    public $uid, $name, $username, $password, $email, $email_sig, $user_tsi, $from_company,
           $from_location, $from_voicenumber, $from_faxnumber, $coverpage_id, $audiofile,
           $faxperpageinbox, $faxperpagearchive, $superuser, $can_del, $last_mod, $last_login,
           $last_ip, $language, $modemdevs, $didrouting, $faxcats, $pwdexpire, $pwdcycle,
           $pwd_reuse, $is_admin, $wasreset, $acc_enabled, $deleted, $any_modem;
}

class UserPasswordsBridge extends MDBObjectBridge {
    protected $table_id_name = 'upid';
    protected $table_name = 'UserPasswords';
    public $upid, $uid, $pwdhash;
}

class AddressBookBridge extends MDBObjectBridge {
    protected $table_id_name = 'abook_id';
    protected $table_name = 'AddressBook';
    public $abook_id, $company;
}

class AddressBookEmailBridge extends MDBObjectBridge {
    protected $table_id_name = 'abookemail_id';
    protected $table_name = 'AddressBookEmail';
    public $abookemail_id, $abook_id, $contact_name, $contact_email;
}

class AddressBookFAXBridge extends MDBObjectBridge {
    protected $table_id_name = 'abookfax_id';
    protected $table_name = 'AddressBookFAX';
    public $abookfax_id, $abook_id, $faxnumber, $email, $description, $to_person,
           $to_location, $to_voicenumber, $faxcatid, $printer, $faxfrom, $faxto;
}

class ModemsBridge extends MDBObjectBridge {
    protected $table_id_name = 'devid';
    protected $table_name = 'Modems';
    public $devid, $device, $alias, $contact, $printer, $faxcatid;
}

class CoverPagesBridge extends MDBObjectBridge {
    protected $table_id_name = 'cover_id';
    protected $table_name = 'CoverPages';
    public $cover_id, $title, $file;
}

class DIDRouteBridge extends MDBObjectBridge {
    protected $table_id_name = 'didr_id';
    protected $table_name = 'DIDRoute';
    public $didr_id, $routecode, $alias, $contact, $printer, $faxcatid;
}

class BarcodeRouteBridge extends MDBObjectBridge {
    protected $table_id_name = 'barcode_id';
    protected $table_name = 'BarcodeRoute';
    public $barcode_id, $barcode, $alias, $contact, $printer, $faxcatid;
}

class FaxArchiveBridge extends MDBObjectBridge {
    protected $table_id_name = 'fid';
    protected $table_name = 'FaxArchive';
    public $fid, $faxnumid, $companyid, $faxpath, $pages, $faxcatid, $didr_id,
           $description, $lastoperation, $lastmoduser, $lastmoddate, $archstamp,
           $modemdev, $userid, $origfaxnum, $inbox, $faxcontent;
}

class FaxCategoryBridge extends MDBObjectBridge {
    protected $table_id_name = 'catid';
    protected $table_name = 'FaxCategory';
    public $catid, $name;
}

class SysLogBridge extends MDBObjectBridge {
    protected $table_id_name = 'syslogid';
    protected $table_name = 'SysLog';
    public $syslogid, $logdate, $logtext;
}

class DynConfBridge extends MDBObjectBridge {
    protected $table_id_name = 'dynconf_id';
    protected $table_name = 'DynConf';
    public $dynconf_id, $device, $callid;
}
