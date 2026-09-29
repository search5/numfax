"""ActiveRecord data models replacing classes.php entities."""

from __future__ import annotations

from typing import Any

from namifax.db.base import MDBObject
from namifax.db.engine import DatabaseEngine


class DistroList(MDBObject):
    table_name = "DistroList"
    table_id_name = "dl_id"

    def __init__(self, db: DatabaseEngine | None = None, **kwargs: Any) -> None:
        super().__init__(db)
        self.dl_id: int | None = None
        self.listname: str = ""
        self.listdata: str | None = None
        self.lastmod_date: str | None = None
        self.lastmod_user: int | None = None
        self.set_vars(kwargs)


class UserAccount(MDBObject):
    table_name = "UserAccount"
    table_id_name = "uid"

    def __init__(self, db: DatabaseEngine | None = None, **kwargs: Any) -> None:
        super().__init__(db)
        self.uid: int | None = None
        self.name: str | None = None
        self.username: str = ""
        self.password: str = ""
        self.email: str = ""
        self.email_sig: str | None = None
        self.user_tsi: str | None = None
        self.from_company: str | None = None
        self.from_location: str | None = None
        self.from_voicenumber: str | None = None
        self.from_faxnumber: str | None = None
        self.coverpage_id: int | None = None
        self.audiofile: str | None = None
        self.faxperpageinbox: int | None = None
        self.faxperpagearchive: int | None = None
        self.superuser: bool = False
        self.can_del: bool = False
        self.last_mod: str | None = None
        self.last_login: str | None = None
        self.last_ip: str | None = None
        self.language: str = "en"
        self.modemdevs: str | None = None
        self.didrouting: str | None = None
        self.faxcats: str | None = None
        self.pwdexpire: str | None = None
        self.pwdcycle: int = 0
        self.pwd_reuse: bool = False
        self.is_admin: bool = False
        self.wasreset: bool = False
        self.acc_enabled: bool = True
        self.deleted: bool = False
        self.any_modem: bool = False
        self.set_vars(kwargs)


class UserPasswords(MDBObject):
    table_name = "UserPasswords"
    table_id_name = "upid"

    def __init__(self, db: DatabaseEngine | None = None, **kwargs: Any) -> None:
        super().__init__(db)
        self.upid: int | None = None
        self.uid: int | None = None
        self.pwdhash: str = ""
        self.set_vars(kwargs)


class AddressBook(MDBObject):
    table_name = "AddressBook"
    table_id_name = "abook_id"

    def __init__(self, db: DatabaseEngine | None = None, **kwargs: Any) -> None:
        super().__init__(db)
        self.abook_id: int | None = None
        self.company: str = ""
        self.set_vars(kwargs)


class AddressBookEmail(MDBObject):
    table_name = "AddressBookEmail"
    table_id_name = "abookemail_id"

    def __init__(self, db: DatabaseEngine | None = None, **kwargs: Any) -> None:
        super().__init__(db)
        self.abookemail_id: int | None = None
        self.abook_id: int | None = None
        self.contact_name: str | None = None
        self.contact_email: str = ""
        self.set_vars(kwargs)


class AddressBookFAX(MDBObject):
    table_name = "AddressBookFAX"
    table_id_name = "abookfax_id"

    def __init__(self, db: DatabaseEngine | None = None, **kwargs: Any) -> None:
        super().__init__(db)
        self.abookfax_id: int | None = None
        self.abook_id: int | None = None
        self.faxnumber: str = ""
        self.email: str | None = None
        self.description: str | None = None
        self.to_person: str | None = None
        self.to_location: str | None = None
        self.to_voicenumber: str | None = None
        self.faxcatid: int | None = None
        self.faxfrom: int = 0
        self.faxto: int = 0
        self.printer: str | None = None
        self.set_vars(kwargs)


class Modems(MDBObject):
    table_name = "Modems"
    table_id_name = "devid"

    def __init__(self, db: DatabaseEngine | None = None, **kwargs: Any) -> None:
        super().__init__(db)
        self.devid: int | None = None
        self.device: str = ""
        self.alias: str | None = None
        self.contact: str | None = None
        self.printer: str | None = None
        self.faxcatid: int | None = None
        self.set_vars(kwargs)


class CoverPages(MDBObject):
    table_name = "CoverPages"
    table_id_name = "cover_id"

    def __init__(self, db: DatabaseEngine | None = None, **kwargs: Any) -> None:
        super().__init__(db)
        self.cover_id: int | None = None
        self.title: str = ""
        self.file: str = ""
        self.set_vars(kwargs)


class DIDRoute(MDBObject):
    table_name = "DIDRoute"
    table_id_name = "didr_id"

    def __init__(self, db: DatabaseEngine | None = None, **kwargs: Any) -> None:
        super().__init__(db)
        self.didr_id: int | None = None
        self.routecode: str = ""
        self.alias: str | None = None
        self.contact: str | None = None
        self.printer: str | None = None
        self.faxcatid: int | None = None
        self.set_vars(kwargs)


class BarcodeRoute(MDBObject):
    table_name = "BarcodeRoute"
    table_id_name = "barcode_id"

    def __init__(self, db: DatabaseEngine | None = None, **kwargs: Any) -> None:
        super().__init__(db)
        self.barcode_id: int | None = None
        self.barcode: str = ""
        self.alias: str | None = None
        self.contact: str | None = None
        self.printer: str | None = None
        self.faxcatid: int | None = None
        self.set_vars(kwargs)


class FaxArchive(MDBObject):
    table_name = "FaxArchive"
    table_id_name = "fid"

    def __init__(self, db: DatabaseEngine | None = None, **kwargs: Any) -> None:
        super().__init__(db)
        self.fid: int | None = None
        self.faxnumid: int | None = None
        self.companyid: int | None = None
        self.faxpath: str = ""
        self.pages: int | None = None
        self.faxcatid: int | None = None
        self.didr_id: int | None = None
        self.description: str | None = None
        self.lastoperation: str | None = None
        self.lastmoduser: int | None = None
        self.lastmoddate: str | None = None
        self.archstamp: str | None = None
        self.modemdev: str | None = None
        self.userid: int | None = None
        self.origfaxnum: str | None = None
        self.faxcontent: str | None = None
        self.inbox: bool = True
        self.set_vars(kwargs)


class FaxCategory(MDBObject):
    table_name = "FaxCategory"
    table_id_name = "catid"

    def __init__(self, db: DatabaseEngine | None = None, **kwargs: Any) -> None:
        super().__init__(db)
        self.catid: int | None = None
        self.name: str = ""
        self.set_vars(kwargs)


class SysLog(MDBObject):
    table_name = "SysLog"
    table_id_name = "syslogid"

    def __init__(self, db: DatabaseEngine | None = None, **kwargs: Any) -> None:
        super().__init__(db)
        self.syslogid: int | None = None
        self.logdate: str | None = None
        self.logtext: str = ""
        self.set_vars(kwargs)


class DynConf(MDBObject):
    table_name = "DynConf"
    table_id_name = "dynconf_id"

    def __init__(self, db: DatabaseEngine | None = None, **kwargs: Any) -> None:
        super().__init__(db)
        self.dynconf_id: int | None = None
        self.device: str | None = None
        self.callid: str | None = None
        self.set_vars(kwargs)
