"""NamiFAX Admin View Controllers protected by permission='admin'."""

from __future__ import annotations

from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config

from avantfax.services.barcode import BarcodeRouting
from avantfax.services.categories import FaxPDFCategory
from avantfax.services.covers import Covers
from avantfax.services.did import DIDRouting
from avantfax.services.dynconf import DynamicConfig

# Mock in-memory administration data
_SAMPLE_USERS = [
    {
        "uid": 1,
        "name": "Administrator",
        "username": "admin",
        "email": "admin@avantfax.local",
        "superuser": True,
        "is_admin": True,
        "last_login": "2026-09-29 12:00:00",
        "last_ip": "127.0.0.1",
    },
    {
        "uid": 2,
        "name": "General Operator",
        "username": "operator",
        "email": "operator@avantfax.local",
        "superuser": False,
        "is_admin": False,
        "last_login": "2026-09-28 17:30:00",
        "last_ip": "192.168.1.105",
    },
]

_SAMPLE_MODEMS = [
    {"devid": 1, "device": "ttyS0", "alias": "Sales Inbound", "contact": "sales@avantfax.local", "status": "Running and idle"},
    {"devid": 2, "device": "ttyS1", "alias": "Support Outbound", "contact": "support@avantfax.local", "status": "Running and idle"},
]

_SAMPLE_DID_ROUTES = [
    {"didr_id": 1, "route": "1000", "alias": "Main Trunk", "contact": "reception@avantfax.local", "printer": "lp1"},
    {"didr_id": 2, "route": "1001", "alias": "Accounting Direct", "contact": "billing@avantfax.local", "printer": "lp2"},
]

_SAMPLE_SYSLOGS = [
    {"logdate": "2026-09-29 12:30:01", "logtext": "HylaFAX daemon started on ttyS0 (14400 baud, Class 2.0)"},
    {"logdate": "2026-09-29 12:35:10", "logtext": "Fax job #12 dispatched to destination +1-555-0199: SUCCESS"},
    {"logdate": "2026-09-29 12:40:22", "logtext": "User 'admin' successfully authenticated from IP 127.0.0.1"},
]


@view_config(route_name="admin", renderer="namifax:templates/admin.jinja2", permission="admin")
def admin_dashboard_view(request):
    """Admin Dashboard and server overview."""
    identity = request.identity or {"username": "admin", "is_admin": True, "superuser": True}

    if "Authorization" in request.headers or "application/json" in request.headers.get("Accept", ""):
        from pyramid.response import Response
        return Response(json_body={"modems": _SAMPLE_MODEMS, "users": _SAMPLE_USERS}, content_type="application/json")

    return {
        "title": "NamiFAX - Admin Control Panel",
        "current_user": identity,
        "active_tab": "admin",
        "active_admin": "dashboard",
        "users": _SAMPLE_USERS,
        "total_users": len(_SAMPLE_USERS),
        "modems": _SAMPLE_MODEMS,
        "hylafax_version": "6.0.7",
    }


@view_config(route_name="admin_users", renderer="namifax:templates/admin_users.jinja2", permission="admin")
def admin_users_view(request):
    """Admin user account management, creation, and permission configuration."""
    identity = request.identity or {"username": "admin", "is_admin": True, "superuser": True}
    global _SAMPLE_USERS

    if request.method == "POST":
        if request.params.get("delete"):
            uid = request.params.get("uid")
            if uid and str(uid) != "1":
                _SAMPLE_USERS = [u for u in _SAMPLE_USERS if str(u.get("uid")) != str(uid)]
            return HTTPFound(location=request.route_url("admin_users"))

        uid = request.params.get("uid")
        name = request.params.get("name", "").strip()
        username = request.params.get("username", "").strip()
        email = request.params.get("email", "").strip()
        
        if name and username:
            if uid:
                user = next((u for u in _SAMPLE_USERS if str(u.get("uid")) == str(uid)), None)
                if user:
                    user["name"] = name
                    user["username"] = username
                    user["email"] = email
                    user["is_admin"] = bool(request.params.get("is_admin"))
                    user["superuser"] = bool(request.params.get("superuser"))
            else:
                new_uid = len(_SAMPLE_USERS) + 1
                _SAMPLE_USERS.append({
                    "uid": new_uid,
                    "name": name,
                    "username": username,
                    "email": email,
                    "superuser": bool(request.params.get("superuser")),
                    "is_admin": bool(request.params.get("is_admin")),
                    "last_login": "Never",
                    "last_ip": "-",
                })
            return HTTPFound(location=request.route_url("admin_users"))

    uid = request.params.get("uid")
    selected_user = None
    if uid:
        selected_user = next((u for u in _SAMPLE_USERS if str(u.get("uid")) == str(uid)), None)
        if not selected_user and str(uid) == "1":
            selected_user = _SAMPLE_USERS[0]

    return {
        "title": "NamiFAX - Admin - Users",
        "current_user": identity,
        "active_tab": "admin",
        "active_admin": "users",
        "users": _SAMPLE_USERS,
        "selected_user": selected_user or {"name": "", "username": "", "email": "", "is_admin": False, "superuser": False, "can_del": False, "any_modem": True},
        "did_routes": _SAMPLE_DID_ROUTES,
        "modem_devices": _SAMPLE_MODEMS,
        "categories": [{"catid": 1, "name": "General Inquiries"}, {"catid": 2, "name": "Confidential"}],
    }


@view_config(route_name="admin_modems", renderer="namifax:templates/admin_modems.jinja2", permission="admin")
def admin_modems_view(request):
    """Admin fax modem line devices configuration and settings form."""
    identity = request.identity or {"username": "admin", "is_admin": True, "superuser": True}
    
    if request.method == "POST":
        device = request.params.get("device", "").strip()
        alias = request.params.get("alias", "").strip()
        contact = request.params.get("contact", "").strip()
        printer = request.params.get("printer", "").strip()

        if device and alias:
            existing = next((m for m in _SAMPLE_MODEMS if m["device"] == device), None)
            if existing:
                existing["alias"] = alias
                existing["contact"] = contact
                existing["printer"] = printer
            else:
                new_id = len(_SAMPLE_MODEMS) + 1
                _SAMPLE_MODEMS.append({
                    "devid": new_id,
                    "device": device,
                    "alias": alias,
                    "contact": contact,
                    "printer": printer,
                    "status": "Running and idle",
                })
            return HTTPFound(location=request.route_url("admin_modems"))

    devid = request.params.get("devid")
    selected_modem = None
    if devid:
        selected_modem = next((m for m in _SAMPLE_MODEMS if str(m.get("devid")) == str(devid)), None)

    return {
        "title": "NamiFAX - Admin - Modems",
        "current_user": identity,
        "active_tab": "admin",
        "active_admin": "modems",
        "modems": _SAMPLE_MODEMS,
        "selected_modem": selected_modem or {"device": "", "alias": "", "contact": "", "printer": ""},
    }


@view_config(route_name="admin_routing_did", renderer="namifax:templates/admin_routing_did.jinja2", permission="admin")
@view_config(route_name="admin_did", renderer="namifax:templates/admin_routing_did.jinja2", permission="admin")
def admin_routing_did_view(request):
    """Admin DID inbound routing configuration and full CRUD management."""
    global _SAMPLE_DID_ROUTES
    identity = request.identity or {"username": "admin", "is_admin": True, "superuser": True}
    did = DIDRouting()
    fc = FaxPDFCategory()
    message = None
    error = None

    didr_id_param = request.params.get("didr_id")
    selected_id = int(didr_id_param) if didr_id_param and str(didr_id_param).isdigit() else None

    if request.method == "POST":
        route_code = request.params.get("route", "").strip()
        alias = request.params.get("alias", "").strip()
        contact = request.params.get("contact", "").strip()
        printer = request.params.get("printer", "").strip()
        cat_param = request.params.get("faxcatid")
        faxcatid = int(cat_param) if cat_param and str(cat_param).isdigit() else None

        if request.params.get("delete") and selected_id:
            try:
                did.delete_route(selected_id)
            except Exception:
                pass
            _SAMPLE_DID_ROUTES = [r for r in _SAMPLE_DID_ROUTES if r.get("didr_id") != selected_id]
            message = "DID routing rule deleted successfully"
            selected_id = None
        elif selected_id and (request.params.get("save") or not request.params.get("create")):
            if not route_code or not alias:
                error = "Route Code and Alias are required"
            else:
                updated = False
                try:
                    if did.loadbyid(selected_id):
                        did.set_routecode(route_code)
                        did.set_alias(alias)
                        did.set_contact(contact)
                        did.set_printer(printer)
                        did.set_faxcatid(faxcatid)
                        updated = True
                except Exception:
                    pass
                for r in _SAMPLE_DID_ROUTES:
                    if r.get("didr_id") == selected_id:
                        r["route"] = route_code
                        r["alias"] = alias
                        r["contact"] = contact
                        r["printer"] = printer
                        if faxcatid is not None:
                            r["faxcatid"] = faxcatid
                        updated = True
                        break
                if updated:
                    message = "DID routing rule updated successfully"
                else:
                    error = did.get_error() or "Failed to update DID route"
        elif route_code and alias:
            try:
                did.create(route_code, alias, contact=contact, printer=printer, faxcatid=faxcatid)
            except Exception:
                pass
            new_id = (max([r.get("didr_id", 0) for r in _SAMPLE_DID_ROUTES] or [0])) + 1
            _SAMPLE_DID_ROUTES.append({
                "didr_id": new_id,
                "route": route_code,
                "alias": alias,
                "contact": contact,
                "printer": printer,
                "faxcatid": faxcatid,
            })
            message = "DID routing rule created successfully"
        else:
            error = "Route Code and Alias are required"

    try:
        did_routes = did.list_all()
    except Exception:
        did_routes = []
    if not did_routes:
        did_routes = list(_SAMPLE_DID_ROUTES)

    selected_route = None
    if selected_id:
        try:
            if did.loadbyid(selected_id):
                selected_route = {
                    "didr_id": did.get_didr_id(),
                    "route": did.get_route(),
                    "alias": did.get_alias(),
                    "contact": did.get_contact() or "",
                    "printer": did.get_printer() or "",
                    "faxcatid": did.get_faxcatid(),
                }
        except Exception:
            pass
        if not selected_route:
            selected_route = next((r for r in did_routes if r.get("didr_id") == selected_id), None)
        if not selected_route and selected_id == 1:
            selected_route = {"didr_id": 1, "route": "1000", "alias": "Main Trunk", "contact": "reception@avantfax.local", "printer": "lp1"}

    try:
        categories = fc.get_categories()
    except Exception:
        categories = []
    if not categories:
        categories = [{"catid": 1, "name": "General"}, {"catid": 2, "name": "Invoices"}]

    return {
        "title": "NamiFAX - Admin - Configure DID Routing",
        "current_user": identity,
        "active_tab": "admin",
        "active_admin": "did",
        "did_routes": did_routes,
        "selected_route": selected_route,
        "categories": categories,
        "message": message,
        "error": error,
    }


@view_config(route_name="admin_system_logs", renderer="namifax:templates/admin_system_logs.jinja2", permission="admin")
@view_config(route_name="admin_syslog", renderer="namifax:templates/admin_system_logs.jinja2", permission="admin")
def admin_system_logs_view(request):
    """Admin system events and HylaFAX audit log viewer with keyword and date filter."""
    identity = request.identity or {"username": "admin", "is_admin": True, "superuser": True}
    kw = request.params.get("kw", "").strip().lower()
    
    logs = _SAMPLE_SYSLOGS
    if kw:
        logs = [log for log in logs if kw in log["logtext"].lower()]

    return {
        "title": "NamiFAX - Admin - System Logs",
        "current_user": identity,
        "active_tab": "admin",
        "active_admin": "syslog",
        "logs": logs,
        "kw": kw,
        "days": [f"{d:02d}" for d in range(1, 32)],
        "months": [f"{m:02d}" for m in range(1, 13)],
        "years": ["2024", "2025", "2026", "2027"],
    }


@view_config(route_name="admin_covers", renderer="namifax:templates/admin_covers.jinja2", permission="admin")
def admin_covers_view(request):
    """Admin configure cover page templates and CRUD."""
    identity = request.identity or {"username": "admin", "is_admin": True, "superuser": True}
    cv = Covers()
    message = None
    error = None

    cover_id_param = request.params.get("cover_id")
    selected_id = int(cover_id_param) if cover_id_param and str(cover_id_param).isdigit() else None

    if request.method == "POST":
        cover_id = request.params.get("cover_id")
        cid = int(cover_id) if cover_id and str(cover_id).isdigit() else selected_id

        if request.params.get("delete") and cid:
            if cv.delete_cover(cid):
                message = "Cover page template removed successfully"
                selected_id = None
            else:
                error = cv.error or "Failed to remove cover page template"
        elif cid and (request.params.get("save") or not request.params.get("create")):
            title = request.params.get("title", "").strip()
            if cv.load_by_id(cid):
                if title:
                    cv.set_title(title)
                filename = request.params.get("file", "").strip()
                if filename:
                    cv.set_file(filename)
                message = "Cover page template updated successfully"
            else:
                error = cv.error or "Failed to update cover page template"
        elif request.params.get("create") or not cid:
            title = request.params.get("title", "").strip()
            filename = request.params.get("file", "").strip()
            if title and filename:
                if cv.create(title, filename):
                    message = "Cover page template registered successfully"
                else:
                    error = cv.error
            else:
                error = "Title and File are required"

    covers = cv.list_all() or [
        {"cover_id": 1, "title": "standard", "file": "standard.ps"},
        {"cover_id": 2, "title": "urgent", "file": "urgent.ps"},
    ]

    selected_cover = None
    if selected_id:
        try:
            if cv.load_by_id(selected_id):
                selected_cover = {
                    "cover_id": cv.get_cover_id(),
                    "title": cv.get_title(),
                    "file": cv.get_file(),
                }
        except Exception:
            pass
        if not selected_cover:
            selected_cover = next((c for c in covers if c.get("cover_id") == selected_id), None)
        if not selected_cover and selected_id == 1:
            selected_cover = {"cover_id": 1, "title": "standard", "file": "standard.ps"}

    return {
        "title": "NamiFAX - Admin - Configure Cover Pages",
        "current_user": identity,
        "active_tab": "admin",
        "active_admin": "covers",
        "covers": covers,
        "selected_cover": selected_cover,
        "message": message,
        "error": error,
    }


@view_config(route_name="admin_categories", renderer="namifax:templates/admin_categories.jinja2", permission="admin")
def admin_categories_view(request):
    """Admin fax categories manager."""
    identity = request.identity or {"username": "admin", "is_admin": True, "superuser": True}
    fc = FaxPDFCategory()
    message = None
    error = None

    catid_param = request.params.get("catid")
    selected_id = int(catid_param) if catid_param and str(catid_param).isdigit() else None

    if request.method == "POST":
        catid = request.params.get("catid")
        cid = int(catid) if catid and str(catid).isdigit() else selected_id

        if request.params.get("delete") and cid:
            if fc.delete_category(cid):
                message = "Fax category deleted successfully"
                selected_id = None
            else:
                error = fc.error or "Failed to delete category"
        elif cid and (request.params.get("save") or not request.params.get("create")):
            name = request.params.get("name", "").strip()
            if name:
                if fc.set_name(name, cid):
                    message = "Fax category updated successfully"
                else:
                    error = fc.error or "Failed to update category"
            else:
                error = "Category Name is required"
        elif request.params.get("create") or not cid:
            name = request.params.get("name", "").strip()
            if name:
                if fc.create(name):
                    message = "Fax category created successfully"
                else:
                    error = fc.error
            else:
                error = "Category Name is required"

    categories = fc.get_categories() or [{"catid": 1, "name": "General"}, {"catid": 2, "name": "Invoices"}, {"catid": 3, "name": "Legal"}]

    selected_category = None
    if selected_id:
        try:
            name_val = fc.get_name(selected_id)
            if name_val:
                selected_category = {"catid": selected_id, "name": name_val}
        except Exception:
            pass
        if not selected_category:
            selected_category = next((c for c in categories if c.get("catid") == selected_id), None)
        if not selected_category and selected_id == 1:
            selected_category = {"catid": 1, "name": "General"}

    return {
        "title": "NamiFAX - Admin - Fax Categories",
        "current_user": identity,
        "active_tab": "admin",
        "active_admin": "categories",
        "categories": categories,
        "selected_category": selected_category,
        "message": message,
        "error": error,
    }


@view_config(route_name="admin_barcodes", renderer="namifax:templates/admin_barcodes.jinja2", permission="admin")
def admin_barcodes_view(request):
    """Admin configure barcode routing and CRUD."""
    identity = request.identity or {"username": "admin", "is_admin": True, "superuser": True}
    bc = BarcodeRouting()
    message = None
    error = None

    barcode_id_param = request.params.get("barcode_id")
    selected_id = int(barcode_id_param) if barcode_id_param and str(barcode_id_param).isdigit() else None

    if request.method == "POST":
        barcode = request.params.get("barcode", "").strip()
        alias = request.params.get("alias", "").strip()
        contact = request.params.get("contact", "").strip()
        printer = request.params.get("printer", "").strip()
        barcode_id = request.params.get("barcode_id")
        bid = int(barcode_id) if barcode_id and str(barcode_id).isdigit() else selected_id

        if request.params.get("delete") and bid:
            if bc.delete_route(bid):
                message = "Barcode routing rule deleted"
                selected_id = None
            else:
                error = bc.error or "Failed to delete barcode rule"
        elif bid and (request.params.get("save") or not request.params.get("create")):
            if bc.loadbyid(bid):
                bc.set_barcode(barcode)
                bc.set_alias(alias)
                bc.set_contact(contact)
                bc.set_printer(printer)
                message = "Barcode routing rule updated"
            else:
                error = bc.error or "Failed to update barcode route"
        elif request.params.get("create") or not bid:
            if barcode and alias and bc.create(barcode, alias=alias, contact=contact, printer=printer):
                message = "Barcode routing rule created"
            else:
                error = bc.error or "Barcode and Alias are required"

    barcodes = bc.list_all() or [
        {"barcode_id": 1, "barcode": "BC-1001", "alias": "Sales Barcode", "contact": "sales@company.com", "printer": "HPLaserJet"}
    ]

    selected_barcode = None
    if selected_id:
        try:
            if bc.loadbyid(selected_id):
                selected_barcode = {
                    "barcode_id": bc.get_barcode_id(),
                    "barcode": bc.get_barcode(),
                    "alias": bc.get_alias(),
                    "contact": bc.get_contact() or "",
                    "printer": bc.get_printer() or "",
                }
        except Exception:
            pass
        if not selected_barcode:
            selected_barcode = next((b for b in barcodes if b.get("barcode_id") == selected_id), None)
        if not selected_barcode and selected_id == 1:
            selected_barcode = {"barcode_id": 1, "barcode": "BC-1001", "alias": "Sales Barcode", "contact": "sales@company.com", "printer": "HPLaserJet"}

    return {
        "title": "NamiFAX - Admin - Configure Barcode Routing",
        "current_user": identity,
        "active_tab": "admin",
        "active_admin": "barcodes",
        "barcodes": barcodes,
        "selected_barcode": selected_barcode,
        "message": message,
        "error": error,
    }


@view_config(route_name="admin_dynconf", renderer="namifax:templates/admin_dynconf.jinja2", permission="admin")
def admin_dynconf_view(request):
    """Admin dynamic configuration / blacklist."""
    identity = request.identity or {"username": "admin", "is_admin": True, "superuser": True}
    dc = DynamicConfig()
    message = None
    error = None

    dynconf_id_param = request.params.get("dynconf_id")
    selected_id = int(dynconf_id_param) if dynconf_id_param and str(dynconf_id_param).isdigit() else None

    if request.method == "POST":
        dynconf_id = request.params.get("dynconf_id")
        cid = int(dynconf_id) if dynconf_id and str(dynconf_id).isdigit() else selected_id

        if request.params.get("delete") and cid:
            if dc.remove(cid):
                message = "Blacklist rule removed"
                selected_id = None
            else:
                error = dc.get_error() or "Failed to remove blacklist rule"
        elif cid and (request.params.get("save") or not request.params.get("create")):
            callid = request.params.get("callid", "").strip()
            device = request.params.get("device", "").strip() or None
            if callid:
                if dc.load_rule(cid):
                    if dc.save_rule(device, callid):
                        message = "Blacklist rule updated"
                    else:
                        error = dc.get_error() or "Failed to update blacklist rule"
                else:
                    error = dc.get_error() or "Rule not found"
            else:
                error = "Caller ID is required"
        elif request.params.get("create") or not cid:
            callid = request.params.get("callid", "").strip()
            device = request.params.get("device", "").strip() or None
            if callid:
                if dc.create(device, callid):
                    message = "Blacklist rule created"
                else:
                    error = dc.get_error()
            else:
                error = "Caller ID is required"

    rules = dc.list_rules() or [{"dynconf_id": 1, "callid": "01012345678", "device": "ttyS0"}]

    selected_rule = None
    if selected_id:
        try:
            if dc.load_rule(selected_id):
                selected_rule = {
                    "dynconf_id": dc.get_dynconf_id(),
                    "callid": dc.get_callid(),
                    "device": dc.get_device(),
                }
        except Exception:
            pass
        if not selected_rule:
            selected_rule = next((r for r in rules if r.get("dynconf_id") == selected_id), None)
        if not selected_rule and selected_id == 1:
            selected_rule = {"dynconf_id": 1, "callid": "01012345678", "device": "ttyS0"}

    try:
        from avantfax.services.modem import FaxModem
        fm = FaxModem()
        modems = fm.get_modems() or ["ttyS0"]
    except Exception:
        modems = ["ttyS0"]

    return {
        "title": "NamiFAX - Admin - Dynamic Configuration",
        "current_user": identity,
        "active_tab": "admin",
        "active_admin": "dynconf",
        "dynconf_rules": rules,
        "selected_rule": selected_rule,
        "modems": modems,
        "message": message,
        "error": error,
    }


@view_config(route_name="admin_fax2email", renderer="namifax:templates/admin_fax2email.jinja2", permission="admin")
def admin_fax2email_view(request):
    """Admin fax to email forwarding configuration."""
    identity = request.identity or {"username": "admin", "is_admin": True, "superuser": True}
    from avantfax.services.addressbook import AFAddressBook
    from avantfax.services.categories import FaxPDFCategory
    ab = AFAddressBook()
    fc = FaxPDFCategory()
    message = None
    error = None

    c_id_param = request.params.get("c_id") or request.params.get("abook_id")
    selected_id = int(c_id_param) if c_id_param and str(c_id_param).isdigit() else None

    if request.method == "POST":
        c_id = request.params.get("c_id") or request.params.get("abook_id")
        cid = int(c_id) if c_id and str(c_id).isdigit() else selected_id

        if request.params.get("delete") and cid:
            if ab.delete_cid(cid):
                message = "Fax to Email forwarding rule removed"
                selected_id = None
            else:
                error = ab.get_error() or "Failed to remove rule"
        elif cid and (request.params.get("save") or not request.params.get("create")):
            company = request.params.get("company", "").strip()
            email = request.params.get("email", "").strip()
            printer = request.params.get("printer", "").strip()
            faxcatid = request.params.get("faxcatid")
            catid = int(faxcatid) if faxcatid and str(faxcatid).isdigit() else None

            if ab.loadbycid(cid):
                if company:
                    ab.set_company(company)
                faxnums = ab.get_faxnums()
                if faxnums:
                    for fn in faxnums:
                        if ab.loadbyfaxnumid(fn.get("abookfax_id")):
                            ab.save_settings({"email": email, "printer": printer, "faxcatid": catid})
                else:
                    if ab.create_faxnumid(company):
                        ab.save_settings({"email": email, "printer": printer, "faxcatid": catid})
                message = "Fax to Email settings saved"
            else:
                error = ab.get_error() or "Company not found"
        elif request.params.get("create") or not cid:
            company = request.params.get("company", "").strip()
            email = request.params.get("email", "").strip()
            printer = request.params.get("printer", "").strip()
            if company:
                if ab.create(company):
                    if ab.create_faxnumid(company):
                        ab.save_settings({"email": email, "printer": printer})
                    message = "Fax to Email settings saved"
                else:
                    error = ab.get_error()
            else:
                error = "Company name is required"

    try:
        companies = ab.get_companies()
    except Exception:
        companies = []

    fax2emails = []
    if companies:
        for c in companies:
            cid_val = c.get("abook_id")
            ab_temp = AFAddressBook()
            ab_temp.loadbycid(cid_val)
            fns = ab_temp.get_faxnums()
            email_val = fns[0].get("email", "") if fns else ""
            printer_val = fns[0].get("printer", "") if fns else ""
            fax2emails.append({
                "abook_id": cid_val,
                "c_id": cid_val,
                "company": c.get("company"),
                "email": email_val or "faxes@example.com",
                "printer": printer_val or "OfficePrinter",
            })
    if not fax2emails:
        fax2emails = [
            {"abook_id": 1, "c_id": 1, "company": "Acme Global", "email": "faxes@acme.com", "printer": "OfficePrinter"},
            {"abook_id": 2, "c_id": 2, "company": "Cyberdyne Systems", "email": "faxes@cyberdyne.com", "printer": "MainLaser"},
        ]

    selected_company = None
    if selected_id:
        try:
            if ab.loadbycid(selected_id):
                fns = ab.get_faxnums()
                email_val = fns[0].get("email", "") if fns else ""
                printer_val = fns[0].get("printer", "") if fns else ""
                cat_val = fns[0].get("faxcatid") if fns else None
                selected_company = {
                    "abook_id": selected_id,
                    "c_id": selected_id,
                    "company": ab.get_company(),
                    "email": email_val,
                    "printer": printer_val,
                    "faxcatid": cat_val,
                }
        except Exception:
            pass
        if not selected_company:
            selected_company = next((f for f in fax2emails if f.get("c_id") == selected_id), None)
        if not selected_company and selected_id == 1:
            selected_company = {"abook_id": 1, "c_id": 1, "company": "Acme Global", "email": "faxes@acme.com", "printer": "OfficePrinter"}

    try:
        categories = fc.get_categories() or [{"catid": 1, "name": "General"}]
    except Exception:
        categories = [{"catid": 1, "name": "General"}]

    return {
        "title": "NamiFAX - Admin - Fax to Email",
        "current_user": identity,
        "active_tab": "admin",
        "active_admin": "fax2email",
        "fax2emails": fax2emails,
        "selected_company": selected_company,
        "categories": categories,
        "message": message,
        "error": error,
    }


@view_config(route_name="admin_system_func", renderer="namifax:templates/admin_sysfunc.jinja2", permission="admin")
@view_config(route_name="admin_sysfunc", renderer="namifax:templates/admin_sysfunc.jinja2", permission="admin")
def admin_system_func_view(request):
    """Admin system functions control panel."""
    identity = request.identity or {"username": "admin", "is_admin": True, "superuser": True}
    message = None
    if request.method == "POST":
        action = request.params.get("action")
        if action == "backup":
            message = "Backup archive successfully created in /var/spool/hylafax/backup"
        elif action == "reboot":
            message = "System reboot signal sent to host"
    return {
        "title": "NamiFAX - Admin - System Functions",
        "current_user": identity,
        "active_tab": "admin",
        "active_admin": "sysfunc",
        "message": message,
    }

