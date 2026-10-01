"""NamiFAX Address Book View Controllers."""

from __future__ import annotations

from typing import Any, Optional

from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config

from namifax.i18n import _
from namifax.services.addressbook import AFAddressBook, clean_faxnum
from namifax.services.categories import FaxPDFCategory
from namifax.services.user_account import AFUserAccount

_DETAIL_FIELDS = ("to_person", "to_location", "to_voicenumber", "to_address", "to_zip", "to_city")


def get_all_companies(db: Any = None) -> list[dict[str, Any]]:
    """Every company with its fax numbers (the reserved placeholder is left out)."""
    try:
        ab = AFAddressBook(db=db)
        numbers = ab.numbers_by_company()
        result = []
        for r in ab.get_companies():
            cid = r.get("abook_id")
            own = numbers.get(cid, [])
            first = own[0] if own else {}
            result.append({
                "id": cid,
                "company_id": cid,
                "company": r.get("company") or "",
                "numbers": [n.get("faxnumber") or "" for n in own],
                "faxnumber": first.get("faxnumber") or r.get("faxnum") or "",
                "email": next((n.get("email") for n in own if n.get("email")), None) or r.get("email") or "",
                "to_person": first.get("to_person") or "",
                "to_address": first.get("to_address") or r.get("address") or "",
                "to_city": first.get("to_city") or r.get("city") or "",
                "to_voicenumber": first.get("to_voicenumber") or r.get("phonenum") or "",
                "description": first.get("description") or r.get("description") or "",
            })
        return result
    except Exception:
        return []


@view_config(route_name="addressbook", renderer="namifax:templates/addressbook.jinja2", permission="view")
def addressbook_list_view(request):
    """Display address book companies list with search and '+ New Company' action."""
    identity = request.identity or {"username": "admin", "is_admin": True, "superuser": True}
    query = request.params.get("q", "").strip().lower()

    companies = get_all_companies(request.dbsession)
    if query:
        digits = clean_faxnum(query)
        companies = [c for c in companies
                     if query in c["company"].lower() or (digits and any(digits in n for n in c["numbers"]))
                     or query in c.get("faxnumber", "")]

    return {
        "title": "NamiFAX - Address Book",
        "current_user": identity,
        "active_tab": "addressbook",
        "companies": companies,
        "query": query,
    }


# --- the edit page ------------------------------------------------------------------------------------------------------

def _company_id(params) -> Optional[int]:
    for key in ("abook_id", "id", "company_id", "cid"):
        value = params.get(key)
        if value and str(value).isdigit():
            return int(value)
    return None


def _account(request) -> AFUserAccount:
    identity = request.identity or {}
    account = AFUserAccount(db=request.dbsession)
    uid = identity.get("user_id") or identity.get("uid")
    if uid:
        account.load(int(uid))
    return account


def _categories(request, account: AFUserAccount) -> list[tuple[int, str]]:
    """The categories the user may pick: all of them for an administrator, otherwise those on the account."""
    identity = request.identity or {}
    everything = FaxPDFCategory(db=request.dbsession).get_categories() or []
    if identity.get("is_admin") or identity.get("superuser") or account.dbdata.get("superuser"):
        return [(int(c["catid"]), c.get("name") or "") for c in everything]
    allowed = {int(x) for x in account.get_faxcats() if str(x).isdigit()}
    return [(int(c["catid"]), c.get("name") or "") for c in everything if int(c["catid"]) in allowed]


def _may_delete(request, account: AFUserAccount) -> bool:
    identity = request.identity or {}
    return bool(account.dbdata.get("can_del") or account.dbdata.get("superuser") or identity.get("superuser"))


def _category_value(posted: str, allowed: set, current: Any = None) -> Optional[int]:
    """The category to store: none, a permitted one, or (for a category the user may not use) what was there."""
    posted = (posted or "").strip()
    if not posted:
        return None
    if posted.isdigit() and int(posted) in allowed:
        return int(posted)
    return current


def _page(request, account, *, book: Optional[AFAddressBook] = None, error=None, message=None, values=None) -> dict:
    cid = book.abook_id if book is not None and book.abook_id else None
    company = {"id": cid, "company": (values or {}).get("company") or (book.get_company() if cid else "") or ""}
    return {
        "title": "NamiFAX - Address Book",
        "current_user": request.identity,
        "active_tab": "addressbook",
        "company": company,
        "numbers": book.get_faxnums() if cid else [],
        "categories": _categories(request, account),
        "can_del": _may_delete(request, account),
        "error": error,
        "message": message,
        "values": values or {},
    }


def _save_numbers(book: AFAddressBook, post, allowed: set) -> Optional[str]:
    """Apply the edited rows. A row with an empty number is removed (as in the original); returns an error message."""
    own = {int(n["abookfax_id"]): n for n in book.get_faxnums()}
    problem = None
    ids = post.getall("abookfax_id")
    columns = {key: post.getall(key) for key in ("faxnumber", "description", "faxcatid", *_DETAIL_FIELDS)}
    for i, raw_id in enumerate(ids):
        if not raw_id.isdigit() or int(raw_id) not in own:
            continue                                   # not one of this company's numbers: never touched
        current = own[int(raw_id)]
        number_text = (columns["faxnumber"][i] if i < len(columns["faxnumber"]) else "").strip()
        number = clean_faxnum(number_text)
        if number_text and not number:
            problem = _("Invalid fax number: %(number)s") % {"number": number_text}
            continue
        if not book.loadbyfaxnumid(int(raw_id)):
            continue
        data = {"faxnumber": number}
        for key in ("description", *_DETAIL_FIELDS):
            data[key] = (columns[key][i] if i < len(columns[key]) else "").strip()
        data["faxcatid"] = _category_value(columns["faxcatid"][i] if i < len(columns["faxcatid"]) else "",
                                           allowed, current.get("faxcatid"))
        book.save_settings(data)
    return problem


def _new_number(book: AFAddressBook, number: str, post, allowed: set) -> bool:
    """Add the number typed into the 'new fax number' block, with its details."""
    if not book.create_faxnumid(number):
        return False
    data = {"description": post.get("new_desc", "").strip(),
            "faxcatid": _category_value(post.get("newfaxcatid", ""), allowed)}
    data.update({key: post.get(f"new_{key}", "").strip() for key in _DETAIL_FIELDS})
    return book.save_settings(data)


@view_config(route_name="addressbook_edit", renderer="namifax:templates/addressbook_edit.jinja2", permission="view")
def addressbook_edit_view(request):
    """Add a company, or edit a company and all of its fax numbers (the original addressbook_edit.php)."""
    account = _account(request)
    book = AFAddressBook(db=request.dbsession)
    allowed = {cid for cid, _name in _categories(request, account)}
    cid = _company_id(request.POST if request.method == "POST" else request.params)

    if request.method != "POST":
        if cid and book.loadbycid(cid):
            message = _("Address book entry saved.") if request.params.get("saved") else None
            return _page(request, account, book=book, message=message)
        return _page(request, account)

    post = request.POST
    company_name = post.get("company", "").strip()
    new_number = post.get("new_faxnum") or post.get("faxnumber") or ""
    values = {"company": company_name, "new_faxnum": new_number, "new_desc": post.get("new_desc", ""),
              "newfaxcatid": post.get("newfaxcatid", ""),
              **{f"new_{k}": post.get(f"new_{k}", "") for k in _DETAIL_FIELDS}}

    def saved(target: int):
        return HTTPFound(location=request.route_url("addressbook_edit", _query={"abook_id": target, "saved": "1"}))

    # ---- a new company -------------------------------------------------------------------------------------------
    if not cid:
        if not company_name:
            return _page(request, account, error=_("Please enter a company name"), values=values)
        if not clean_faxnum(new_number):
            return _page(request, account, error=_("Please enter a valid fax number"), values=values)
        if not book.create(company_name):
            return _page(request, account, error=book.get_error(), values=values)
        if not _new_number(book, new_number, post, allowed):
            error = book.get_error()
            book.delete_cid(book.abook_id)              # do not leave a company without its number behind
            return _page(request, account, error=error, values=values)
        return saved(book.abook_id)

    # ---- an existing company ------------------------------------------------------------------------------------
    if not book.loadbycid(cid):
        return HTTPFound(location=request.route_url("addressbook"))

    if post.get("delete"):
        if not _may_delete(request, account):
            return _page(request, account, book=book, error=_("You are not allowed to delete address book entries."))
        if book.delete_company(cid):
            return HTTPFound(location=request.route_url("addressbook"))
        return _page(request, account, book=book, error=book.get_error())

    if not company_name:
        return _page(request, account, book=book, error=_("Please enter a company name"), values=values)
    if not book.set_company(company_name):
        return _page(request, account, book=book, error=book.get_error(), values=values)
    problem = _save_numbers(book, post, allowed)
    book.abook_id = cid                                  # (loading a number may have pointed the helper elsewhere)
    if (post.get("new_faxnum") or "").strip():
        if not _new_number(book, post.get("new_faxnum", ""), post, allowed):
            problem = book.get_error() or problem
    if problem:
        book.loadbycid(cid)
        return _page(request, account, book=book, error=problem, values=values)
    return saved(cid)


@view_config(route_name="emailbook", renderer="namifax:templates/emailbook.jinja2", permission="view")
def emailbook_list_view(request):
    """Display email contacts list directly from database."""
    identity = request.identity or {"username": "admin", "is_admin": True, "superuser": True}
    ab = AFAddressBook(db=request.dbsession)
    contacts = []
    try:
        raw = ab.get_contacts()
        if raw:
            for eid, cstr in raw.items():
                name_part = cstr.split("<")[0].replace('"', '').strip() if "<" in cstr else cstr
                email_part = cstr.split("<")[1].replace(">", "").strip() if "<" in cstr else cstr
                contacts.append({"id": eid, "name": name_part, "email": email_part})
    except Exception:
        pass

    return {
        "title": "- NamiFAX - Email Address Book",
        "current_user": identity,
        "active_tab": "addressbook",
        "contacts": contacts,
    }


@view_config(route_name="emailbook_edit", renderer="namifax:templates/emailbook_edit.jinja2", permission="view")
def emailbook_edit_view(request):
    """Display and handle email contact add / edit form directly with database."""
    identity = request.identity or {"username": "admin", "is_admin": True, "superuser": True}
    ab = AFAddressBook(db=request.dbsession)

    if request.method == "POST":
        params = request.params
        contact_name = params.get("contact_name", "").strip()
        contact_email = params.get("contact_email", "").strip()
        company = params.get("company", "").strip()
        eid = params.get("email_id") or params.get("abookemail_id")

        if params.get("delete") and eid:
            try:
                ab.remove_contact(int(eid))
            except Exception:
                pass
            return HTTPFound(location=request.route_url("emailbook"))

        if eid:
            try:
                eid_val = int(eid)
                from namifax.db.repository import MDBOData
                repo = MDBOData("AddressBookEmail", db=request.dbsession)
                repo.data.set_id(eid_val)
                repo.update_entry({"contact_name": contact_name, "contact_email": contact_email})
            except Exception:
                pass
            return HTTPFound(location=request.route_url("emailbook"))

        if contact_name and contact_email:
            try:
                ab.create_contact(contact_name, contact_email)
            except Exception:
                pass
            return HTTPFound(location=request.route_url("emailbook"))

    contact_id = request.params.get("email_id") or request.params.get("abookemail_id")
    contact = {"id": "", "name": "", "email": "", "company": ""}
    if contact_id:
        try:
            from namifax.db.repository import MDBOData
            repo = MDBOData("AddressBookEmail", db=request.dbsession)
            cid_int = int(contact_id)
            rec = repo.find({"abookemail_id": cid_int}) or repo.find({"email_id": cid_int})
            if rec:
                contact = {
                    "id": rec.get("abookemail_id") or rec.get("email_id") or cid_int,
                    "name": rec.get("contact_name") or rec.get("to_person") or "",
                    "email": rec.get("contact_email") or rec.get("email") or "",
                    "company": "",
                }
        except Exception:
            pass

    return {
        "title": "NamiFAX - Email Book",
        "current_user": identity,
        "active_tab": "addressbook",
        "contact": contact,
    }
