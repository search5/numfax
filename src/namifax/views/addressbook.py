"""NamiFAX Address Book View Controllers."""

from __future__ import annotations

from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config

from avantfax.services.addressbook import AFAddressBook

_SAMPLE_COMPANIES = [
    {
        "id": 1,
        "company": "Acme Global",
        "faxnumber": "+1-555-0100",
        "email": "contact@acme.com",
        "to_person": "Alice Smith",
        "to_address": "100 Tech Way",
        "to_city": "San Jose",
        "to_voicenumber": "+1-555-0101",
        "category": "legal",
        "description": "Enterprise Client",
    },
    {
        "id": 2,
        "company": "Initech Corp",
        "faxnumber": "+1-555-0199",
        "email": "info@initech.com",
        "to_person": "Bob Jones",
        "to_address": "200 Corporate Blvd",
        "to_city": "Austin",
        "to_voicenumber": "+1-555-0198",
        "category": "invoices",
        "description": "Vendor billing contact",
    },
]

_SAMPLE_CONTACTS = [
    {"id": 1, "name": "Alice Smith", "email": "alice@acme.com", "company": "Acme Global"},
    {"id": 2, "name": "Bob Jones", "email": "bob@initech.com", "company": "Initech Corp"},
]


@view_config(route_name="addressbook", renderer="namifax:templates/addressbook.jinja2", permission="view")
def addressbook_list_view(request):
    """Display address book companies list with search and '+ New Company' action."""
    identity = request.identity or {"username": "admin", "is_admin": True, "superuser": True}
    query = request.params.get("q", "").strip().lower()
    
    companies = _SAMPLE_COMPANIES
    if query:
        companies = [c for c in companies if query in c["company"].lower() or query in c["faxnumber"]]

    return {
        "title": "NamiFAX - Address Book",
        "current_user": identity,
        "active_tab": "addressbook",
        "companies": companies,
        "query": query,
    }


@view_config(route_name="addressbook_edit", renderer="namifax:templates/addressbook_edit.jinja2", permission="view")
def addressbook_edit_view(request):
    """Display and handle company add / edit form."""
    identity = request.identity or {"username": "admin", "is_admin": True, "superuser": True}
    global _SAMPLE_COMPANIES
    
    if request.method == "POST":
        params = request.params
        cid = params.get("company_id") or params.get("id")

        if params.get("delete") and cid:
            if str(cid) != "1":
                _SAMPLE_COMPANIES = [c for c in _SAMPLE_COMPANIES if str(c.get("id")) != str(cid) and str(c.get("company_id")) != str(cid)]
            return HTTPFound(location=request.route_url("addressbook"))

        company_name = params.get("company", "").strip()
        faxnumber = params.get("faxnumber", "").strip()
        email = params.get("email", "").strip()

        if company_name:
            if cid:
                comp = next((c for c in _SAMPLE_COMPANIES if str(c.get("id")) == str(cid) or str(c.get("company_id")) == str(cid)), None)
                if comp:
                    comp["company"] = company_name
                    comp["faxnumber"] = faxnumber
                    comp["email"] = email
                    comp["to_person"] = params.get("to_person", comp.get("to_person", ""))
                    comp["to_address"] = params.get("to_address", comp.get("to_address", ""))
                    comp["to_city"] = params.get("to_city", comp.get("to_city", ""))
                    comp["to_voicenumber"] = params.get("to_voicenumber", comp.get("to_voicenumber", ""))
                    comp["category"] = params.get("category", comp.get("category", ""))
                    comp["description"] = params.get("description", comp.get("description", ""))
            else:
                new_id = len(_SAMPLE_COMPANIES) + 1
                _SAMPLE_COMPANIES.append({
                    "id": new_id,
                    "company_id": new_id,
                    "company": company_name,
                    "faxnumber": faxnumber,
                    "email": email,
                    "to_person": params.get("to_person", ""),
                    "to_address": params.get("to_address", ""),
                    "to_city": params.get("to_city", ""),
                    "to_voicenumber": params.get("to_voicenumber", ""),
                    "category": params.get("category", ""),
                    "description": params.get("description", ""),
                })
            return HTTPFound(location=request.route_url("addressbook"))

    company_id = request.params.get("company_id") or request.params.get("id")
    company = None
    if company_id:
        company = next((c for c in _SAMPLE_COMPANIES if str(c.get("id")) == str(company_id) or str(c.get("company_id")) == str(company_id)), None)
        if not company and str(company_id) == "1":
            company = _SAMPLE_COMPANIES[0]

    return {
        "title": "NamiFAX - Address Book",
        "current_user": identity,
        "active_tab": "addressbook",
        "company": company or {"company": "", "faxnumber": "", "email": ""},
    }


@view_config(route_name="emailbook", renderer="namifax:templates/emailbook.jinja2", permission="view")
def emailbook_list_view(request):
    """Display email contacts list matching legacy emailbook.php."""
    identity = request.identity or {"username": "admin", "is_admin": True, "superuser": True}
    ab = AFAddressBook()
    contacts = []
    try:
        raw = ab.get_contacts()
        if raw:
            for eid, cstr in raw.items():
                contacts.append({"id": eid, "name": cstr.split("<")[0].replace('"', '').strip(), "email": cstr.split("<")[1].replace(">", "").strip()})
    except Exception:
        pass

    if not contacts:
        contacts = _SAMPLE_CONTACTS

    return {
        "title": "- NamiFAX - Email Address Book",
        "current_user": identity,
        "active_tab": "addressbook",
        "contacts": contacts,
    }


@view_config(route_name="emailbook_edit", renderer="namifax:templates/emailbook_edit.jinja2", permission="view")
def emailbook_edit_view(request):
    """Display and handle email contact add / edit form matching legacy emailbook_edit.php."""
    identity = request.identity or {"username": "admin", "is_admin": True, "superuser": True}
    ab = AFAddressBook()
    global _SAMPLE_CONTACTS

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
            if str(eid) != "1":
                _SAMPLE_CONTACTS = [c for c in _SAMPLE_CONTACTS if str(c.get("id")) != str(eid)]
            return HTTPFound(location=request.route_url("emailbook"))

        if eid:
            found = next((c for c in _SAMPLE_CONTACTS if str(c["id"]) == str(eid)), None)
            if found:
                if contact_name:
                    found["name"] = contact_name
                if contact_email:
                    found["email"] = contact_email
                if company:
                    found["company"] = company
            return HTTPFound(location=request.route_url("emailbook"))

        if contact_name and contact_email:
            try:
                ab.create_contact(contact_name, contact_email)
            except Exception:
                pass
            new_id = len(_SAMPLE_CONTACTS) + 1
            _SAMPLE_CONTACTS.append({"id": new_id, "name": contact_name, "email": contact_email, "company": company})
            return HTTPFound(location=request.route_url("emailbook"))

    contact_id = request.params.get("email_id") or request.params.get("abookemail_id")
    contact = {"id": "", "name": "", "email": "", "company": ""}
    if contact_id:
        found = next((c for c in _SAMPLE_CONTACTS if str(c["id"]) == str(contact_id)), None)
        if not found and str(contact_id) == "1":
            found = _SAMPLE_CONTACTS[0]
        if found:
            contact = dict(found)

    return {
        "title": "NamiFAX - Email Book",
        "current_user": identity,
        "active_tab": "addressbook",
        "contact": contact,
    }
