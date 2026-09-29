# Contract Specification: Module 09 - classes_entities

## 1. Overview
- **레거시 모듈**: `legacy/avantfax/includes/classes.php` (14개 엔티티 클래스)
- **타깃 모듈**: `src/avantfax/models/entities.py`
- **의존 관계**: 01번 `SQL` (`engine.py`), 08번 `MDBObject` (`base.py`)

---

## 2. Interface Contract (인터페이스 명세)

모든 엔티티 클래스는 `MDBObject`를 상속하며, 고유한 `table_name`과 `table_id_name`(PK 컬럼명)을 가집니다.

| 클래스명 | 테이블명 | PK 컬럼 (`table_id_name`) | 필드 목록 |
| :--- | :--- | :--- | :--- |
| `DistroList` | `DistroList` | `dl_id` | `dl_id`, `listname`, `listdata`, `lastmod_date`, `lastmod_user` |
| `UserAccount` | `UserAccount` | `uid` | `uid`, `name`, `username`, `password`, `email`, `email_sig`, `user_tsi`, `from_company`, `from_location`, `from_voicenumber`, `from_faxnumber`, `coverpage_id`, `audiofile`, `faxperpageinbox`, `faxperpagearchive`, `superuser`, `can_del`, `last_mod`, `last_login`, `last_ip`, `language`, `modemdevs`, `didrouting`, `faxcats`, `pwdexpire`, `pwdcycle`, `pwd_reuse`, `is_admin`, `wasreset`, `acc_enabled`, `deleted`, `any_modem` |
| `UserPasswords` | `UserPasswords` | `upid` | `upid`, `uid`, `pwdhash` |
| `AddressBook` | `AddressBook` | `abook_id` | `abook_id`, `company` |
| `AddressBookEmail` | `AddressBookEmail` | `abookemail_id` | `abookemail_id`, `abook_id`, `contact_name`, `contact_email` |
| `AddressBookFAX` | `AddressBookFAX` | `abookfax_id` | `abookfax_id`, `abook_id`, `faxnumber`, `email`, `description`, `to_person`, `to_location`, `to_voicenumber`, `faxcatid`, `faxfrom`, `faxto`, `printer` |
| `Modems` | `Modems` | `devid` | `devid`, `device`, `alias`, `contact`, `printer`, `faxcatid` |
| `CoverPages` | `CoverPages` | `cover_id` | `cover_id`, `title`, `file` |
| `DIDRoute` | `DIDRoute` | `didr_id` | `didr_id`, `routecode`, `alias`, `contact`, `printer`, `faxcatid` |
| `BarcodeRoute` | `BarcodeRoute` | `barcode_id` | `barcode_id`, `barcode`, `alias`, `contact`, `printer`, `faxcatid` |
| `FaxArchive` | `FaxArchive` | `fid` | `fid`, `faxnumid`, `companyid`, `faxpath`, `pages`, `faxcatid`, `didr_id`, `description`, `lastoperation`, `lastmoduser`, `lastmoddate`, `archstamp`, `modemdev`, `userid`, `origfaxnum`, `faxcontent`, `inbox` |
| `FaxCategory` | `FaxCategory` | `catid` | `catid`, `name` |
| `SysLog` | `SysLog` | `syslogid` | `syslogid`, `logdate`, `logtext` |
| `DynConf` | `DynConf` | `dynconf_id` | `dynconf_id`, `device`, `callid` |

---

## 3. Idiomatic Transformation Rules
1. **Pydantic / Typed Dict 호환**: 데이터 직렬화/역직렬화를 위한 `to_dict()`, `from_dict()` 지원.
2. **Type Annotations**: 모든 필드에 명시적 Python 타입 힌트 부여.
3. **ActiveRecord CRUD 연동**: `base.py`의 `MDBObject`를 통해 `save()`, `load()`, `delete()` 즉시 사용 가능.
