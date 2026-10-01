"""NamiFAX Inbox and Fax Viewer Views."""

from __future__ import annotations

import os

from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.response import Response
from pyramid.view import view_config

from namifax.services.addressbook import AFAddressBook
from namifax.services.archive_in import ArchiveIn
from namifax.views.admin import get_all_admin_modems


@view_config(route_name="inbox", renderer="namifax:templates/inbox.jinja2", permission="view")
def inbox_view(request):
    """Render inbox list matching NamiFAX layout and action items."""
    identity = request.identity or {"username": "admin", "is_admin": True, "superuser": True}

    faxes = []
    if not request.params.get("empty"):
        arc = ArchiveIn()
        superuser = bool(identity.get("superuser") or identity.get("is_admin"))
        devices = None if superuser else identity.get("modemdevs")
        if isinstance(devices, str):
            devices = [d.strip() for d in devices.split(",") if d.strip()]

        rows = arc.list_inbox(devices=devices)
        if rows:
            ab = AFAddressBook()
            for r in rows:
                fid = r.get("fid")
                cname = None
                if r.get("companyid"):
                    try:
                        if ab.loadbycid(r.get("companyid")):
                            cname = ab.get_company()
                    except Exception:
                        pass
                if not cname and r.get("faxnumid"):
                    try:
                        if ab.loadbyfaxnumid(r.get("faxnumid")):
                            cname = ab.get_company()
                    except Exception:
                        pass
                faxes.append({
                    "id": fid,
                    "company": cname or r.get("company") or "",
                    "origfaxnum": r.get("origfaxnum") or "-",
                    "archstamp": r.get("archstamp") or "",
                    "modemdev": r.get("modemdev") or "",
                    "pages": r.get("pages") or 1,
                    "description": r.get("description") or "",
                })

    if "Authorization" in request.headers or "application/json" in request.headers.get("Accept", ""):
        return Response(json_body={"items": faxes, "total_count": len(faxes)}, content_type="application/json")

    modem_list = get_all_admin_modems()

    return {
        "title": "- NamiFAX - Inbox",
        "current_user": identity,
        "active_tab": "inbox",
        "faxes": faxes,
        "total_faxes": len(faxes),
        "num_inbox": len(faxes),
        "modem_list": modem_list,
    }


@view_config(route_name="viewfax", renderer="namifax:templates/viewfax.jinja2", permission="view")
def viewfax_view(request):
    """Render fax preview dialog."""
    identity = request.identity or {"username": "admin", "is_admin": True}
    fid = request.params.get("fid", "1")
    pages = 1
    archstamp = ""
    modemdev = ""
    company = ""

    try:
        arc = ArchiveIn()
        if fid.isdigit() and arc.load_fax(int(fid)):
            pages = arc.get_pages() or 1
            archstamp = arc.get_archstamp() or ""
            modemdev = arc.get_modemdev() or ""
            if arc.get_companyid():
                try:
                    ab = AFAddressBook()
                    if ab.loadbycid(arc.get_companyid()):
                        company = ab.get_company()
                except Exception:
                    pass
            if not company and arc.get_faxnumid():
                try:
                    ab = AFAddressBook()
                    if ab.loadbyfaxnumid(arc.get_faxnumid()):
                        company = ab.get_company()
                except Exception:
                    pass
    except Exception:
        pass

    return {
        "title": "NamiFAX - View Fax",
        "current_user": identity,
        "active_tab": "inbox",
        "fid": fid,
        "pages": pages,
        "archstamp": archstamp,
        "modemdev": modemdev,
        "company": company,
    }


@view_config(route_name="fax_download", permission="view")
def fax_download_view(request):
    """Stream PDF or TIFF binary file matching legacy file.php and pdf.php."""
    fid = request.matchdict.get("fid", "1")
    fmt = request.params.get("format", "pdf")
    content_type = "application/pdf" if fmt == "pdf" else "image/tiff"

    # Attempt to locate actual archived fax file on disk
    file_bytes: bytes | None = None
    try:
        arc = ArchiveIn()
        if arc.load_fax(int(fid)):
            file_path = arc.get_pdfpath() if fmt == "pdf" else arc.get_tiffpath()
            if file_path and os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    file_bytes = f.read()
    except Exception:
        pass

    if file_bytes is None:
        raise HTTPNotFound("Fax document file not found")

    res = Response(body=file_bytes, content_type=content_type)
    res.headers["Content-Disposition"] = f'inline; filename="fax_{fid}.{fmt}"'
    return res


@view_config(route_name="fax_rotate", renderer="json", permission="view")
@view_config(route_name="rotate", renderer="json", permission="view")
def fax_rotate_view(request):
    """Rotate fax pages by 90 degrees matching legacy rotate.php."""
    fid = request.matchdict.get("fid") or request.params.get("fid", "1")
    arc = ArchiveIn()
    try:
        if fid and arc.load_fax(int(fid)):
            arc.rotate_fax()
    except Exception:
        pass

    if request.params.get("redirect") == "inbox":
        return HTTPFound(location=request.route_url("inbox"))
    return {"status": "ok", "fid": str(fid), "rotation": 90}


@view_config(route_name="setcompany", permission="view")
def setcompany_view(request):
    """Assign faxnumid to received fax matching legacy setcompany.php."""
    fid = request.params.get("fid", "1")
    faxnumid = request.params.get("faxnumid")

    if fid and faxnumid:
        arc = ArchiveIn()
        ab = AFAddressBook()
        try:
            if arc.load_fax(int(fid)):
                arc.set_faxnumid(int(faxnumid))
            if ab.loadbyfaxnumid(int(faxnumid)):
                ab.inc_faxfrom()
        except Exception:
            pass

    return HTTPFound(location=request.route_url("inbox"))
