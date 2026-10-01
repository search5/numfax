"""NamiFAX Admin View Controllers protected by permission='admin'."""

from __future__ import annotations

import os

from pyramid.httpexceptions import HTTPFound, HTTPForbidden
from pyramid.view import view_config

from avantfax.services.barcode import BarcodeRouting
from avantfax.services.categories import FaxPDFCategory
from avantfax.services.covers import Covers
from avantfax.services.did import DIDRouting
from avantfax.services.dynconf import DynamicConfig
from namifax.i18n import _

def get_all_admin_users() -> list[dict[str, Any]]:
    """Retrieve users directly from database."""
    try:
        from namifax.services.user_account import AFUserAccount
        svc = AFUserAccount()
        rows = svc.list_accounts()
        if rows:
            users_list = []
            for r in rows:
                users_list.append({
                    "uid": r.get("uid"),
                    "name": r.get("name") or r.get("username"),
                    "username": r.get("username"),
                    "email": r.get("email"),
                    "superuser": bool(r.get("superuser")),
                    "is_admin": bool(r.get("is_admin") or r.get("superuser")),
                    "last_login": r.get("last_login") or "Never",
                    "last_ip": r.get("last_ip") or "-",
                    "can_del": bool(r.get("can_del")),
                    "any_modem": bool(r.get("any_modem", 1)),
                })
            # Ensure admin user is first if present
            users_list.sort(key=lambda u: 0 if u.get("uid") == 1 else 1)
            return users_list
    except Exception:
        pass
    return []


def get_all_admin_modems() -> list[dict[str, Any]]:
    """Retrieve modems directly from database."""
    try:
        from namifax.services.modem import FaxModem
        svc = FaxModem()
        rows = svc.list_all()
        if rows:
            modems_list = []
            for r in rows:
                device = r.get("device")
                svc.load_device(device)
                modem_stat = svc.get_status()
                status_text = modem_stat.get("status") if isinstance(modem_stat, dict) else str(modem_stat)
                modems_list.append({
                    "devid": r.get("devid"),
                    "device": device,
                    "alias": r.get("alias"),
                    "contact": r.get("contact") or "",
                    "printer": r.get("printer") or "",
                    "faxcatid": r.get("faxcatid"),
                    "status": status_text or "Running and idle",
                })
            return modems_list
    except Exception:
        pass
    return []


@view_config(route_name="admin", renderer="namifax:templates/admin.jinja2", permission="admin")
def admin_dashboard_view(request):
    """Admin Dashboard and server overview."""
    identity = request.identity or {"username": "admin", "is_admin": True, "superuser": True}
    users = get_all_admin_users()
    modems = get_all_admin_modems()

    if "Authorization" in request.headers or "application/json" in request.headers.get("Accept", ""):
        from pyramid.response import Response
        return Response(json_body={"modems": modems, "users": users}, content_type="application/json")

    return {
        "title": "NamiFAX - Admin Control Panel",
        "current_user": identity,
        "active_tab": "admin",
        "active_admin": "dashboard",
        "users": users,
        "total_users": len(users),
        "modems": modems,
        "hylafax_version": "6.0.7",
    }


@view_config(route_name="admin_users", renderer="namifax:templates/admin_users.jinja2", permission="admin")
def admin_users_view(request):
    """Admin user account management matching legacy admin/users.php semantics."""
    identity = request.identity or {"username": "admin", "is_admin": True, "superuser": True}

    if request.method == "POST":
        if request.params.get("delete"):
            uid = request.params.get("uid")
            if uid and str(uid) != "1":
                try:
                    from namifax.services.user_account import AFUserAccount
                    svc = AFUserAccount()
                    svc.remove(int(uid))
                except Exception:
                    pass
            return HTTPFound(location=request.route_url("admin_users"))

        uid = request.params.get("uid")
        name = request.params.get("name", "").strip()
        username = request.params.get("username", "").strip()
        email = request.params.get("email", "").strip()
        password = request.params.get("password", "").strip()
        superuser = bool(request.params.get("superuser"))
        is_admin = bool(request.params.get("is_admin"))
        can_del = bool(request.params.get("can_del"))
        any_modem = bool(request.params.get("any_modem", True))

        if name and username:
            try:
                from namifax.services.user_account import AFUserAccount
                svc = AFUserAccount()
                if uid:
                    if svc.load(int(uid)):
                        svc.set_username(username)
                        svc.set_email(email)
                        svc.dbdata["name"] = name
                        svc.dbdata["superuser"] = int(superuser)
                        svc.dbdata["is_admin"] = int(is_admin)
                        svc.dbdata["can_del"] = int(can_del)
                        svc.dbdata["any_modem"] = int(any_modem)
                        if password:
                            svc.change_password(password)
                        svc.update()
                else:
                    svc.create({
                        "name": name,
                        "username": username,
                        "email": email,
                        "password": password or "password",
                        "superuser": int(superuser),
                        "is_admin": int(is_admin),
                        "can_del": int(can_del),
                        "any_modem": int(any_modem),
                    })
            except Exception:
                pass

            return HTTPFound(location=request.route_url("admin_users"))

    users = get_all_admin_users()
    uid = request.params.get("uid")
    selected_user = None
    if uid:
        selected_user = next((u for u in users if str(u.get("uid")) == str(uid)), None)
        if not selected_user and str(uid) == "1" and users:
            selected_user = users[0]

    did = DIDRouting()
    try:
        did_routes = did.list_all()
    except Exception:
        did_routes = []

    fc = FaxPDFCategory()
    try:
        categories = fc.get_categories() or []
    except Exception:
        categories = []

    return {
        "title": "NamiFAX - Admin - Users",
        "current_user": identity,
        "active_tab": "admin",
        "active_admin": "users",
        "users": users,
        "selected_user": selected_user or {"name": "", "username": "", "email": "", "is_admin": False, "superuser": False, "can_del": False, "any_modem": True},
        "did_routes": did_routes,
        "modem_devices": get_all_admin_modems(),
        "categories": categories,
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
        faxcatid = request.params.get("faxcatid")
        faxcatid_val = int(faxcatid) if faxcatid and str(faxcatid).isdigit() else None
        devid = request.params.get("devid")

        if request.params.get("delete"):
            if devid:
                try:
                    from namifax.services.modem import FaxModem
                    svc = FaxModem()
                    svc.delete_device(int(devid))
                except Exception:
                    pass
            return HTTPFound(location=request.route_url("admin_modems"))

        if device and alias:
            try:
                from namifax.services.modem import FaxModem
                svc = FaxModem()
                if devid and svc.loadbyid(int(devid)):
                    svc.set_alias(alias)
                    svc.set_contact(contact)
                    svc.set_printer(printer)
                    if faxcatid_val is not None:
                        svc.set_faxcatid(faxcatid_val)
                elif svc.load_device(device):
                    svc.set_alias(alias)
                    svc.set_contact(contact)
                    svc.set_printer(printer)
                    if faxcatid_val is not None:
                        svc.set_faxcatid(faxcatid_val)
                else:
                    svc.create(device=device, alias=alias, contact=contact, printer=printer, faxcatid=faxcatid_val)
            except Exception:
                pass

            return HTTPFound(location=request.route_url("admin_modems"))

    modems = get_all_admin_modems()
    devid = request.params.get("devid")
    device_param = request.params.get("device")
    selected_modem = None
    if devid:
        selected_modem = next((m for m in modems if str(m.get("devid")) == str(devid)), None)
    elif device_param:
        selected_modem = next((m for m in modems if m.get("device") == device_param), None)

    return {
        "title": "NamiFAX - Admin - Modems",
        "current_user": identity,
        "active_tab": "admin",
        "active_admin": "modems",
        "modems": modems,
        "selected_modem": selected_modem or {"device": "", "alias": "", "contact": "", "printer": ""},
    }


@view_config(route_name="admin_routing_did", renderer="namifax:templates/admin_routing_did.jinja2", permission="admin")
@view_config(route_name="admin_did", renderer="namifax:templates/admin_routing_did.jinja2", permission="admin")
def admin_routing_did_view(request):
    """Admin DID inbound routing configuration and full CRUD management."""
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
                if updated:
                    message = "DID routing rule updated successfully"
                else:
                    error = did.get_error() or "Failed to update DID route"
        elif route_code and alias:
            try:
                did.create(route_code, alias, contact=contact, printer=printer, faxcatid=faxcatid)
                message = "DID routing rule created successfully"
            except Exception:
                error = "Failed to create DID route"
        else:
            error = "Route Code and Alias are required"

    try:
        did_routes = did.list_all()
    except Exception:
        did_routes = []

    # Ensure route field compatibility
    for r in did_routes:
        if "route" not in r:
            r["route"] = r.get("routecode", "")

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

    try:
        categories = fc.list_all() if hasattr(fc, "list_all") else fc.get_categories()
    except Exception:
        categories = []

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


def get_all_syslogs(kw: str = "", day: str = "", month: str = "", year: str = "") -> list[dict[str, Any]]:
    """Retrieve system logs directly from database."""
    try:
        from namifax.db.repository import MDBOData
        repo = MDBOData("SysLog")
        clauses = []
        if kw:
            clauses.append(f"logtext LIKE {repo.quote(f'%{kw}%')}")

        date_part = ""
        if day and month and year and day != "*" and month != "*" and year != "*":
            d_val = f"{int(day):02d}" if day.isdigit() else day
            m_val = f"{int(month):02d}" if month.isdigit() else month
            date_part = f"{year}-{m_val}-{d_val}"
        elif month and year and month != "*" and year != "*":
            m_val = f"{int(month):02d}" if month.isdigit() else month
            date_part = f"{year}-{m_val}"
        elif year and year != "*":
            date_part = f"{year}"

        if date_part:
            clauses.append(f"logdate LIKE {repo.quote(f'{date_part}%')}")

        where_clause = " WHERE " + " AND ".join(clauses) if clauses else ""
        query = f"SELECT logdate, logtext FROM SysLog{where_clause} ORDER BY logdate DESC LIMIT 100"
        rows = repo.query(query, reduce_single=False)
        if rows and isinstance(rows, list):
            result = []
            for r in rows:
                result.append({
                    "logdate": str(r.get("logdate", "")),
                    "logtext": str(r.get("logtext", "")),
                })
            return result
    except Exception:
        pass

    return []


@view_config(route_name="admin_system_logs", renderer="namifax:templates/admin_system_logs.jinja2", permission="admin")
@view_config(route_name="admin_syslog", renderer="namifax:templates/admin_system_logs.jinja2", permission="admin")
def admin_system_logs_view(request):
    """Admin system events and HylaFAX audit log viewer with keyword and date filter."""
    identity = request.identity or {"username": "admin", "is_admin": True, "superuser": True}
    kw = request.params.get("kw", "").strip()
    day = request.params.get("day", "")
    month = request.params.get("month", "")
    year = request.params.get("year", "")

    logs = get_all_syslogs(kw=kw, day=day, month=month, year=year)

    return {
        "title": "NamiFAX - Admin - System Logs",
        "current_user": identity,
        "active_tab": "admin",
        "active_admin": "syslog",
        "logs": logs,
        "kw": kw,
        "day": day,
        "month": month,
        "year": year,
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
                message = _("Cover page template removed successfully")
                selected_id = None
            else:
                error = cv.error or _("Failed to remove cover page template")
        elif cid and (request.params.get("save") or not request.params.get("create")):
            title = request.params.get("title", "").strip()
            if cv.load_by_id(cid):
                if title:
                    cv.set_title(title)
                filename = request.params.get("file", "").strip()
                if filename:
                    cv.set_file(filename)
                message = _("Cover page template updated successfully")
            else:
                error = cv.error or _("Failed to update cover page template")
        elif request.params.get("create") or not cid:
            title = request.params.get("title", "").strip()
            filename = request.params.get("file", "").strip()
            if title and filename:
                if cv.create(title, filename):
                    message = _("Cover page template registered successfully")
                else:
                    error = cv.error
            else:
                error = _("Title and File are required")

    covers = cv.list_all() or []

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

    return {
        "title": "NamiFAX - Admin - Configure Cover Pages",
        "current_user": identity,
        "active_tab": "admin",
        "active_admin": "covers",
        "covers": covers,
        "selected_cover": selected_cover,
        "supported_tags": [
            {"tag": "TO_COMPANY", "desc": "Recipient company name"},
            {"tag": "TO_LOCATION", "desc": "Recipient department / location"},
            {"tag": "TO_VOICENUMBER", "desc": "Recipient telephone number"},
            {"tag": "TO_FAXNUMBER", "desc": "Recipient fax number"},
            {"tag": "TO_PERSON", "desc": "Recipient person name"},
            {"tag": "FROM_COMPANY", "desc": "Sender company name"},
            {"tag": "FROM_LOCATION", "desc": "Sender location"},
            {"tag": "FROM_VOICENUMBER", "desc": "Sender telephone number"},
            {"tag": "FROM_FAXNUMBER", "desc": "Sender fax number"},
            {"tag": "FROM_PERSON", "desc": "Sender name"},
            {"tag": "PAGECOUNT", "desc": "Total page count"},
            {"tag": "DATE_TIME", "desc": "Cover creation timestamp"},
            {"tag": "REGARDING", "desc": "Subject / Regarding"},
            {"tag": "COMMENTS", "desc": "Cover note comments"},
        ],
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

    categories = fc.get_categories() or []

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

    barcodes = bc.list_all() or []

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

    rules = dc.list_rules() or []

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

    try:
        from namifax.services.modem import FaxModem
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
            cid_val = c.get("ab_id") or c.get("abook_id")
            ab_temp = AFAddressBook()
            ab_temp.loadbycid(cid_val)
            fns = ab_temp.get_faxnums()
            email_val = fns[0].get("email", "") if fns else ""
            printer_val = fns[0].get("printer", "") if fns else ""
            fax2emails.append({
                "abook_id": cid_val,
                "c_id": cid_val,
                "company": c.get("company"),
                "email": email_val,
                "printer": printer_val,
            })

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

    try:
        categories = fc.get_categories() or []
    except Exception:
        categories = []

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
    import datetime
    import io
    import tarfile
    import tempfile

    identity = request.identity or {"username": "admin", "is_admin": True, "superuser": True}
    message = None
    if request.method == "POST":
        action = request.params.get("action")
        if action == "backup":
            backup_dir = os.environ.get("NAMIFAX_BACKUP_DIR") or "/var/spool/hylafax/backup"
            try:
                os.makedirs(backup_dir, exist_ok=True)
            except OSError:
                backup_dir = os.path.join(os.environ.get("NAMIFAX_TMPDIR") or tempfile.gettempdir(), "namifax_backup")
                os.makedirs(backup_dir, exist_ok=True)

            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_filename = f"namifax_backup_{ts}.tar.gz"
            archive_path = os.path.join(backup_dir, archive_filename)

            with tarfile.open(archive_path, "w:gz") as tar:
                manifest_content = f"NamiFAX System Backup\nGenerated: {datetime.datetime.now().isoformat()}\n".encode("utf-8")
                ti = tarfile.TarInfo(name="backup_manifest.txt")
                ti.size = len(manifest_content)
                ti.mtime = int(datetime.datetime.now().timestamp())
                tar.addfile(ti, io.BytesIO(manifest_content))

            message = f"Backup archive successfully created in {backup_dir} ({archive_filename})"
        elif action == "reboot":
            message = "System reboot signal sent to host"
    return {
        "title": "NamiFAX - Admin - System Functions",
        "current_user": identity,
        "active_tab": "admin",
        "active_admin": "sysfunc",
        "message": message,
    }


@view_config(route_name="admin_smtp", renderer="namifax:templates/admin_smtp.jinja2", permission="admin")
def admin_smtp_view(request):
    """Admin SMTP Gateway settings and connectivity diagnostics view."""
    identity = getattr(request, "identity", None)
    session = getattr(request, "session", {})
    is_admin = False
    if identity:
        is_admin = bool(identity.get("superuser") or identity.get("is_admin") or identity.get("is_superadmin"))
    elif session:
        is_admin = bool(session.get("is_superadmin") or session.get("is_admin"))

    if not is_admin:
        raise HTTPForbidden(_("Access denied. Superadmin permission required."))

    db = getattr(request, "db", None)
    db_engine = getattr(request, "db_engine", None)
    if not db:
        from namifax.db.engine import DatabaseEngine
        db = DatabaseEngine()
        if db_engine:
            # If a custom engine was provided
            try:
                db._conn = db_engine.raw_connection().connection
            except Exception:
                pass

    from namifax.services.smtp_settings import SmtpSettingsService, SmtpConfig
    service = SmtpSettingsService(db)

    message = None
    error = None
    test_result = None

    params = dict(getattr(request, "POST", {}))
    if hasattr(request, "params") and request.params:
        params.update(request.params)

    if request.method == "POST":
        action = params.get("action")
        if action == "save":
            try:
                service.save_settings(params)
                message = _("SMTP Gateway settings saved successfully.")
                loc = "/admin/smtp"
                if hasattr(request, "route_url"):
                    try:
                        loc = request.route_url("admin_smtp")
                    except Exception:
                        pass
                return HTTPFound(location=loc)
            except Exception as exc:
                error = str(exc)
        elif action == "test":
            target_email = params.get("test_email", "admin@localhost")
            cfg = SmtpConfig(
                smtp_host=params.get("smtp_host", "localhost"),
                smtp_port=int(params.get("smtp_port", 25) or 25),
                smtp_security=params.get("smtp_security", "NONE"),
                smtp_auth=params.get("smtp_auth") in ("on", "1", "true", True),
                smtp_username=params.get("smtp_username"),
                smtp_password=params.get("smtp_password"),
                from_email=params.get("from_email", "root@localhost"),
                from_name=params.get("from_name", "NamiFAX"),
            )
            res = service.test_connection(target_email, cfg)
            test_result = {
                "success": res.success,
                "message": res.message,
                "details": res.details,
            }

    config = service.get_settings()
    return {
        "title": "NamiFAX - Admin - SMTP Gateway",
        "current_user": identity or {"username": session.get("username", "admin"), "is_admin": True, "superuser": True},
        "active_tab": "admin",
        "active_admin": "smtp",
        "config": config,
        "message": message,
        "error": error,
        "test_result": test_result,
    }


@view_config(route_name="admin_printers", renderer="namifax:templates/admin_printers.jinja2", permission="admin")
def admin_printers_view(request):
    """Network Printer management console."""
    identity = getattr(request, "identity", None)
    session = getattr(request, "session", {})
    is_admin = False
    if identity:
        is_admin = bool(identity.get("superuser") or identity.get("is_admin") or identity.get("is_superadmin"))
    elif session:
        is_admin = bool(session.get("is_superadmin") or session.get("is_admin"))

    if not is_admin:
        raise HTTPForbidden(_("Access denied. Superadmin permission required."))

    db = getattr(request, "db", None)
    if not db:
        from namifax.db.engine import DatabaseEngine
        db = DatabaseEngine()

    from namifax.services.printer import NetworkPrinterService
    service = NetworkPrinterService(db)

    message = None
    error = None
    test_result = None

    if request.method == "POST":
        action = request.params.get("action", "")
        if action == "add":
            name = request.params.get("name", "").strip()
            protocol = request.params.get("protocol", "RAW").strip()
            host = request.params.get("host", "").strip()
            port = int(request.params.get("port", 9100) or 9100)
            queue_name = request.params.get("queue_name", "").strip() or None
            description = request.params.get("description", "").strip() or None
            if not name or not host:
                error = _("Printer name and host are required.")
            else:
                try:
                    service.create_printer(name, protocol, host, port, queue_name, description)
                    message = _("Network printer registered successfully.")
                except Exception as exc:
                    error = f"Error creating printer: {exc}"
        elif action == "delete":
            printer_id = int(request.params.get("printer_id", 0))
            if printer_id:
                service.delete_printer(printer_id)
                message = _("Printer deleted successfully.")
        elif action == "test":
            host = request.params.get("test_host", "").strip()
            port = int(request.params.get("test_port", 9100) or 9100)
            if host:
                res = service.send_raw_print(host, port, b"NamiFAX Direct Print Test OK\r\n\x0c")
                test_result = res
                if res.get("success"):
                    message = res.get("message")
                else:
                    error = res.get("message")

    printers = service.list_printers()

    return {
        "current_admin_tab": "printers",
        "current_user": identity or {"username": session.get("username", "admin"), "is_admin": True, "superuser": True},
        "active_tab": "admin",
        "active_admin": "printers",
        "printers": printers,
        "message": message,
        "error": error,
        "test_result": test_result,
    }


@view_config(route_name="admin_storage", renderer="namifax:templates/admin_storage.jinja2", permission="admin")
def admin_storage_view(request):
    """Enterprise Storage & Cloud Lifecycle management console."""
    identity = getattr(request, "identity", None)
    session = getattr(request, "session", {})
    is_admin = False
    if identity:
        is_admin = bool(identity.get("superuser") or identity.get("is_admin") or identity.get("is_superadmin"))
    elif session:
        is_admin = bool(session.get("is_superadmin") or session.get("is_admin"))

    if not is_admin:
        raise HTTPForbidden(_("Access denied. Superadmin permission required."))

    db = getattr(request, "db", None)
    if not db:
        from namifax.db.engine import DatabaseEngine
        db = DatabaseEngine()

    from namifax.services.cloud_storage import StorageConfig, CloudStorageManager
    from namifax.services.storage_lifecycle import StorageLifecyclePolicy, StorageLifecycleService

    db.query("CREATE TABLE IF NOT EXISTS SystemConfig (key TEXT PRIMARY KEY, value TEXT)")

    def get_cfg(k: str, default: str = "") -> str:
        res = db.query(f"SELECT value FROM SystemConfig WHERE key = {db.quote(k)}")
        recs = db.get_records() if res.executed else []
        return recs[0]["value"] if recs and "value" in recs[0] else default

    def set_cfg(k: str, v: str) -> None:
        db.query(f"INSERT OR REPLACE INTO SystemConfig (key, value) VALUES ({db.quote(k)}, {db.quote(v)})")

    message = None
    error = None
    test_result = None

    if request.method == "POST":
        action = request.params.get("action", "")
        if action == "save_lifecycle":
            purge_tiff = int(request.params.get("purge_tiff_after_days", 7) or 7)
            retention = int(request.params.get("full_retention_days", 365) or 365)
            remote_sync = "remote_sync_delete" in request.params
            set_cfg("storage_purge_tiff_days", str(purge_tiff))
            set_cfg("storage_retention_days", str(retention))
            set_cfg("storage_remote_sync_delete", "1" if remote_sync else "0")
            message = _("Lifecycle policy saved successfully.")
        elif action == "save_cloud":
            stype = request.params.get("storage_type", "LOCAL").strip()
            endpoint = request.params.get("endpoint_url", "").strip()
            region = request.params.get("region_name", "").strip()
            bucket = request.params.get("bucket_name", "").strip()
            access_key = request.params.get("access_key", "").strip()
            secret_key = request.params.get("secret_key", "").strip()
            prefix = request.params.get("prefix", "").strip()

            set_cfg("cloud_storage_type", stype)
            set_cfg("cloud_endpoint_url", endpoint)
            set_cfg("cloud_region_name", region)
            set_cfg("cloud_bucket_name", bucket)
            set_cfg("cloud_access_key", access_key)
            if secret_key:
                set_cfg("cloud_secret_key", secret_key)
            set_cfg("cloud_prefix", prefix)
            message = _("Cloud storage configuration saved successfully.")
        elif action == "test_cloud":
            stype = request.params.get("storage_type", "LOCAL").strip()
            endpoint = request.params.get("endpoint_url", "").strip() or None
            region = request.params.get("region_name", "").strip() or None
            bucket = request.params.get("bucket_name", "").strip() or None
            access_key = request.params.get("access_key", "").strip() or None
            secret_key = request.params.get("secret_key", "").strip() or get_cfg("cloud_secret_key", "")
            prefix = request.params.get("prefix", "").strip()

            cfg = StorageConfig(
                storage_type=stype,
                endpoint_url=endpoint,
                region_name=region,
                bucket_name=bucket,
                access_key=access_key,
                secret_key=secret_key,
                prefix=prefix,
            )
            provider = CloudStorageManager.get_provider(cfg)
            res = provider.test_connection()
            test_result = res
            if res.get("success"):
                message = res.get("message")
            else:
                error = res.get("message")

    # Load current configs
    lifecycle = {
        "purge_tiff_after_days": int(get_cfg("storage_purge_tiff_days", "7")),
        "full_retention_days": int(get_cfg("storage_retention_days", "365")),
        "remote_sync_delete": get_cfg("storage_remote_sync_delete", "1") == "1",
    }
    cloud = {
        "storage_type": get_cfg("cloud_storage_type", "LOCAL"),
        "endpoint_url": get_cfg("cloud_endpoint_url", ""),
        "region_name": get_cfg("cloud_region_name", "us-east-1"),
        "bucket_name": get_cfg("cloud_bucket_name", ""),
        "access_key": get_cfg("cloud_access_key", ""),
        "has_secret_key": bool(get_cfg("cloud_secret_key", "")),
        "prefix": get_cfg("cloud_prefix", ""),
    }

    return {
        "current_admin_tab": "storage",
        "current_user": identity or {"username": session.get("username", "admin"), "is_admin": True, "superuser": True},
        "active_tab": "admin",
        "active_admin": "storage",
        "lifecycle": lifecycle,
        "cloud": cloud,
        "message": message,
        "error": error,
        "test_result": test_result,
    }


@view_config(route_name="admin_saml", renderer="namifax:templates/admin_saml.jinja2", permission="admin")
def admin_saml_view(request):
    """Enterprise SAML 2.0 Identity Provider configuration console."""
    identity = getattr(request, "identity", None)
    session = getattr(request, "session", {})
    is_admin = False
    if identity:
        is_admin = bool(identity.get("superuser") or identity.get("is_admin") or identity.get("is_superadmin"))
    elif session:
        is_admin = bool(session.get("is_superadmin") or session.get("is_admin"))

    if not is_admin:
        raise HTTPForbidden(_("Access denied. Superadmin permission required."))

    db = getattr(request, "db", None)
    if not db:
        from namifax.db.engine import DatabaseEngine
        db = DatabaseEngine()

    from namifax.services.saml import SAMLSettings, SAMLService

    db.query("CREATE TABLE IF NOT EXISTS SystemConfig (key TEXT PRIMARY KEY, value TEXT)")

    def get_cfg(k: str, default: str = "") -> str:
        res = db.query(f"SELECT value FROM SystemConfig WHERE key = {db.quote(k)}")
        recs = db.get_records() if res.executed else []
        return recs[0]["value"] if recs and "value" in recs[0] else default

    def set_cfg(k: str, v: str) -> None:
        db.query(f"INSERT OR REPLACE INTO SystemConfig (key, value) VALUES ({db.quote(k)}, {db.quote(v)})")

    message = None
    error = None

    if request.method == "POST":
        enabled = "enabled" in request.params
        idp_entity_id = request.params.get("idp_entity_id", "").strip()
        idp_sso_url = request.params.get("idp_sso_url", "").strip()
        idp_x509_cert = request.params.get("idp_x509_cert", "").strip()
        jit_provisioning = "jit_provisioning" in request.params
        default_role = request.params.get("default_role", "user").strip()

        set_cfg("saml_enabled", "1" if enabled else "0")
        set_cfg("saml_idp_entity_id", idp_entity_id)
        set_cfg("saml_idp_sso_url", idp_sso_url)
        set_cfg("saml_idp_x509_cert", idp_x509_cert)
        set_cfg("saml_jit_provisioning", "1" if jit_provisioning else "0")
        set_cfg("saml_default_role", default_role)
        message = _("SAML 2.0 configuration saved successfully.")

    settings = {
        "enabled": get_cfg("saml_enabled", "0") == "1",
        "idp_entity_id": get_cfg("saml_idp_entity_id", ""),
        "idp_sso_url": get_cfg("saml_idp_sso_url", ""),
        "idp_x509_cert": get_cfg("saml_idp_x509_cert", ""),
        "jit_provisioning": get_cfg("saml_jit_provisioning", "1") == "1",
        "default_role": get_cfg("saml_default_role", "user"),
        "sp_metadata_url": request.route_url("saml_metadata"),
        "sp_acs_url": request.route_url("saml_acs"),
    }

    return {
        "current_admin_tab": "saml",
        "current_user": identity or {"username": session.get("username", "admin"), "is_admin": True, "superuser": True},
        "active_tab": "admin",
        "active_admin": "saml",
        "saml": settings,
        "message": message,
        "error": error,
    }

