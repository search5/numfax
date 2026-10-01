from __future__ import annotations

import re
from typing import Any

from namifax.common.validators import is_valid_email
from namifax.db.engine import DatabaseEngine
from namifax.db.repository import MDBOData

DEFAULT_LANG = {
    "ASSIGN_MISSING": "Please enter a company name",
    "COMPANY_EXISTS": "Company already exists",
    "FAXNUMID_NOT_CREATED": "Fax number could not be created",
    "NO_COMPANY_FOR_FAXNUM": "No company configured for fax number",
    "REGWARN_MAIL": "Please enter a valid e-mail address.",
    "NAME_MISSING": "Please enter a name",
    "REGWARN_MAIL_EXISTS": "A contact with that e-mail address already exists",
}


def clean_faxnum(faxnum: str | None) -> str:
    """Strip all formatting characters except digits and leading +."""
    if not faxnum:
        return ""
    return re.sub(r"[^0-9+]", "", str(faxnum))


class AFAddressBook:
    """Unified service for companies, fax number routing, and email contacts.

    ``db`` is a SQLAlchemy ``Session`` (portable across SQLite, MySQL, MariaDB and PostgreSQL) or the legacy
    ``DatabaseEngine``.
    """

    def __init__(
        self,
        db: Any = None,
        engine: DatabaseEngine | None = None,
        lang: dict[str, str] | None = None,
    ) -> None:
        self.db = db or engine
        self.lang = lang or DEFAULT_LANG

        self.addressbook = MDBOData("AddressBook", db=self.db)
        self.addressbookfax = MDBOData("AddressBookFAX", db=self.db)
        self.addressbookemail = MDBOData("AddressBookEmail", db=self.db)

        self.abook_id: int | None = None
        self.company: str | None = None
        self.email_array: dict[str, Any] = {}
        self.fax_array: dict[str, Any] = {}
        self.multiple: bool = False
        self.error: str | None = None

        self._contact_queried: bool = False
        self._contact_results: list[dict[str, Any]] = []

    # ---------------- Company Methods ----------------

    def create(self, companyname: str | None) -> bool:
        """Create a new company entry."""
        if not companyname:
            self.error = self.lang.get("ASSIGN_MISSING", "Please enter a company name")
            return False

        self.company = companyname
        lookup = {"company": self.company}

        res = self.addressbook.find(lookup)
        if res:
            if isinstance(res, dict):
                self.abook_id = res.get("abook_id")
            self.error = self.lang.get("COMPANY_EXISTS", "Company already exists")
            return False

        if self.addressbook.new_entry(lookup):
            self.abook_id = self.addressbook.get_id()
            self.error = None
            return True

        self.error = "No abook_id created"
        return False

    def loadbycid(self, cid: int | None) -> bool:
        """Load company by primary key abook_id (cid)."""
        if not cid:
            self.error = "No abook_id loaded"
            return False

        self.abook_id = cid
        data = self.addressbook.find({"abook_id": self.abook_id})
        if data and isinstance(data, dict):
            self.company = data.get("company")
            self.error = None
            return True

        self.abook_id = None
        return False

    def get_companies(self, with_reserved: bool = False) -> list[dict[str, Any]]:
        """Return all companies ordered by company name."""
        return self.addressbook.select(order_by="company")

    def search_companies(self, query: str) -> list[dict[str, Any]]:
        """Search companies matching query string."""
        return self.addressbook.search_text("company", query, order_by="company")

    def totalfaxes(self) -> tuple[int, int] | None:
        """Return (faxfrom, faxto) counts for loaded fax number."""
        if "abookfax_id" not in self.fax_array:
            self.error = "No abookfax_id loaded"
            return None
        return (self.fax_array.get("faxfrom", 0), self.fax_array.get("faxto", 0))

    def get_companyid(self) -> int | None:
        if not self.abook_id:
            self.error = "No abook_id loaded"
            return None
        return self.abook_id

    def set_company(self, companyname: str | None) -> bool:
        """Update company name for loaded company."""
        if not self.abook_id:
            self.error = "No abook_id loaded"
            return False
        if not companyname:
            self.error = self.lang.get("ASSIGN_MISSING", "Please enter a company name")
            return False

        self.company = companyname
        self.addressbook.data.set_id(self.abook_id)
        ok = bool(self.addressbook.update_entry({"company": self.company}))
        if ok:
            self.error = None
        return ok

    def delete_cid(self, cid: int | None) -> bool:
        """Delete company by abook_id."""
        if not cid:
            self.error = "No abook_id loaded"
            return False
        self.addressbook.data.set_id(cid)
        return bool(self.addressbook.delete_entry())

    def has_fax2email(self) -> bool:
        """Check if loaded company has email configured for fax2email routing."""
        if not self.abook_id:
            return False
        rows = self.addressbookfax.find({"abook_id": self.abook_id}, reduce_single=False)
        return any(r.get("email") for r in (rows if isinstance(rows, list) else []))

    def get_company(self) -> str | None:
        """Return loaded company name, auto-loading if needed."""
        if not self.abook_id:
            self.error = "No abook_id loaded"
            return None
        if not self.company:
            self.loadbycid(self.abook_id)
        return self.company

    def get_error(self) -> str | None:
        return self.error

    # ---------------- Fax Methods ----------------

    def create_faxnumid(self, faxnumber: str | None) -> bool:
        """Create a new fax number associated with the loaded company."""
        if not self.abook_id:
            self.error = "No abook_id loaded"
            return False

        clean_num = clean_faxnum(faxnumber)
        if not clean_num:
            self.error = "fax number missing"
            return False

        self.fax_array = {"faxnumber": clean_num}
        lookup = {"abook_id": self.abook_id, "faxnumber": clean_num}

        if self.addressbookfax.find(lookup):
            self.error = "Company already has this fax number"
            return False

        if self.addressbookfax.new_entry(lookup):
            self.fax_array["abookfax_id"] = self.addressbookfax.get_id()
            self.error = None
            return True

        self.error = self.lang.get("FAXNUMID_NOT_CREATED", "Fax number could not be created")
        return False

    def delete_companyfaxids(self, cid: int | None) -> bool:
        """Delete all fax numbers associated with company."""
        if not cid:
            self.error = "No abook_id sent"
            return False
        self.addressbookfax.delete_where({"abook_id": cid})
        return True

    def delete_faxnumid(self, abookfax_id: int | None) -> bool:
        """Delete specific fax number record."""
        if not abookfax_id:
            self.error = "No abookfax_id sent"
            return False
        self.addressbookfax.data.set_id(abookfax_id)
        return bool(self.addressbookfax.delete_entry())

    def loadbyfaxnumid(self, abookfax_id: int | None) -> bool:
        """Load fax information by abookfax_id."""
        if not abookfax_id:
            self.error = "No faxnumid sent"
            return False

        self.fax_array = {}
        data = self.addressbookfax.find({"abookfax_id": abookfax_id})
        if data and isinstance(data, dict):
            self.fax_array = data
            self.abook_id = data.get("abook_id")
            self.company = None
            self.error = None
            return True

        self.error = self.lang.get("NO_COMPANY_FOR_FAXNUM", "No company configured for fax number")
        return False

    def loadbyfaxnum(self, faxnumber: str | None) -> tuple[bool, bool]:
        """Look up company by fax number. Returns (success, is_multiple)."""
        if not faxnumber:
            self.error = "No faxnumber sent"
            return False, False

        clean_num = clean_faxnum(faxnumber)
        if not clean_num:
            self.error = "No faxnumber sent"
            return False, False

        results = self.addressbookfax.find({"faxnumber": clean_num}, reduce_single=False)
        if results and isinstance(results, list):
            num = len(results)
            if num == 1:
                self.fax_array = results[0]
                self.abook_id = results[0].get("abook_id")
                self.company = None
                self.multiple = False
                return True, False
            elif num > 1:
                self.multiple = True
                return True, True

        template = self.lang.get("NO_COMPANY_FOR_FAXNUM", "No company configured for fax number")
        self.error = f"{template} '{clean_num}'"
        return False, False

    def reassign(self, newcid: int | None) -> bool:
        """Reassign fax numbers from current company to new company, then delete old company."""
        if not newcid or not self.abook_id:
            self.error = "No abook_id loaded"
            return False

        if not self.addressbook.find({"abook_id": newcid}):
            self.error = "Invalid cid"
            return False

        self.addressbookfax.update_where({"abook_id": self.abook_id}, {"abook_id": newcid})
        old_cid = self.abook_id
        self.abook_id = newcid
        self.company = None
        return self.delete_cid(old_cid)

    def save_settings(self, data: dict[str, Any]) -> bool:
        """Save attributes for the loaded fax number."""
        if "abookfax_id" not in self.fax_array:
            self.error = "No abookfax_id loaded"
            return False

        if "faxnumber" in data and not data["faxnumber"]:
            return self.delete_faxnumid(self.fax_array["abookfax_id"])

        self.fax_array.update(data)
        self.addressbookfax.data.set_id(self.fax_array["abookfax_id"])
        ok = bool(self.addressbookfax.update_entry(self.fax_array))
        if ok:
            self.error = None
        return ok

    def get_faxnums(self) -> list[dict[str, Any]]:
        """Return all fax numbers for loaded company."""
        if not self.abook_id:
            self.error = "No abook_id loaded"
            return []
        res = self.addressbookfax.find({"abook_id": self.abook_id}, reduce_single=False)
        return res if isinstance(res, list) else []

    def inc_faxfrom(self) -> bool:
        """Increment count of faxes received from this fax number."""
        if "abookfax_id" not in self.fax_array:
            self.error = "No abookfax_id loaded"
            return False
        new_val = int(self.fax_array.get("faxfrom") or 0) + 1
        return self.save_settings({"faxfrom": new_val})

    def inc_faxto(self) -> bool:
        """Increment count of faxes sent to this fax number."""
        if "abookfax_id" not in self.fax_array:
            self.error = "No abookfax_id loaded"
            return False
        new_val = int(self.fax_array.get("faxto") or 0) + 1
        return self.save_settings({"faxto": new_val})

    def get_faxnumber(self) -> str | None:
        return self.fax_array.get("faxnumber")

    def get_description(self) -> str | None:
        return self.fax_array.get("description")

    def get_category(self) -> int | None:
        return self.fax_array.get("faxcatid")

    def get_printer(self) -> str | None:
        return self.fax_array.get("printer")

    def get_faxnumid(self) -> int | None:
        return self.fax_array.get("abookfax_id")

    def get_email(self) -> str | None:
        return self.fax_array.get("email")

    def get_faxfrom(self) -> int | None:
        return self.fax_array.get("faxfrom")

    def get_faxto(self) -> int | None:
        return self.fax_array.get("faxto")

    def get_to_person(self) -> str | None:
        return self.fax_array.get("to_person")

    def get_to_address(self) -> str | None:
        return self.fax_array.get("to_address")

    def get_to_zip(self) -> str | None:
        return self.fax_array.get("to_zip")

    def get_to_city(self) -> str | None:
        return self.fax_array.get("to_city")

    def get_to_location(self) -> str | None:
        return self.fax_array.get("to_location")

    def get_to_voicenumber(self) -> str | None:
        return self.fax_array.get("to_voicenumber")

    # ---------------- Contact Methods ----------------

    def create_contact(self, name: str | None, email: str | None) -> bool:
        """Create a contact record in AddressBookEmail."""
        if not email or not is_valid_email(email):
            self.error = self.lang.get("REGWARN_MAIL", "Please enter a valid e-mail address.")
            return False

        if not name:
            self.error = self.lang.get("NAME_MISSING", "Please enter a name")
            return False

        if self.addressbookemail.find({"contact_email": email}):
            self.error = self.lang.get("REGWARN_MAIL_EXISTS", "A contact with that e-mail address already exists")
            return False

        payload = {
            "abook_id": self.abook_id,
            "contact_name": name,
            "contact_email": email,
        }
        if self.addressbookemail.new_entry(payload):
            self.email_array["abookemail_id"] = self.addressbookemail.get_id()
            self.email_array["contact_name"] = name
            self.email_array["contact_email"] = email
            self.error = None
            return True

        self.error = "AddressBookEmail contact not created."
        return False

    def create_contacts(self, string: str) -> None:
        """Batch parse semicolon-separated contacts string and create entries."""
        items = [part.strip() for part in string.split(";") if part.strip()]
        for item in items:
            match = re.search(r"^(.*?)\s*<([^>]+)>$", item)
            if match:
                name = match.group(1).strip()
                email = match.group(2).strip()
            else:
                if "@" in item:
                    email = item.strip()
                    name = email.split("@")[0].replace(".", " ").replace("_", " ")
                else:
                    continue
            self.create_contact(name, email)

    def get_contacts(self) -> dict[int, str]:
        """Return mapping of abookemail_id -> formatted contact string."""
        res = self.addressbookemail.select(order_by="contact_name")
        contacts: dict[int, str] = {}
        if res:
            for row in res:
                eid = row.get("abookemail_id")
                cname = row.get("contact_name")
                cemail = row.get("contact_email")
                if eid:
                    contacts[eid] = f'"{cname}" <{cemail}>'
        return contacts

    def make_contact_list_step(self) -> tuple[int, str, str] | None:
        """Step-by-step cursor emulation for contact list."""
        if not self._contact_queried:
            self._contact_results = self.addressbookemail.select(order_by="contact_name")
            self._contact_queried = True

        if self._contact_results:
            data = self._contact_results.pop(0)
            return (
                data.get("abookemail_id", 0),
                data.get("contact_name", ""),
                data.get("contact_email", ""),
            )

        self._contact_queried = False
        return None

    def remove_contact(self, abookemail_id: int | None) -> bool:
        """Remove contact by abookemail_id."""
        if not abookemail_id:
            return False
        self.addressbookemail.data.set_id(abookemail_id)
        return bool(self.addressbookemail.delete_entry())

    def load_contact_by_id(self, abookemail_id: int | None) -> bool:
        """Load contact by abookemail_id."""
        if not abookemail_id:
            self.error = "No abookemail_id loaded"
            return False

        data = self.addressbookemail.find({"abookemail_id": abookemail_id})
        if data and isinstance(data, dict):
            self.email_array = data
            self.error = None
            return True

        self.error = f"Invalid abookemail_id '{abookemail_id}'"
        return False

    def update_contact(self, name: str | None, email: str | None) -> bool:
        """Update loaded contact name and email."""
        eid = self.email_array.get("abookemail_id")
        if not eid:
            self.error = "No abookemail_id loaded"
            return False

        if not email or not is_valid_email(email):
            self.error = self.lang.get("REGWARN_MAIL", "Please enter a valid e-mail address.")
            return False

        if not name:
            self.error = self.lang.get("NAME_MISSING", "Please enter a name")
            return False

        self.email_array["contact_name"] = name
        self.email_array["contact_email"] = email
        self.addressbookemail.data.set_id(eid)
        ok = bool(self.addressbookemail.update_entry(self.email_array))
        if ok:
            self.error = None
        return ok

    def get_contact_name(self) -> str | None:
        return self.email_array.get("contact_name")

    def get_contact_email(self) -> str | None:
        return self.email_array.get("contact_email")


# Modern architectural alias
AddressBookService = AFAddressBook
