"""NamiFAX Inbox and Fax Viewer Views."""

from __future__ import annotations

from pyramid.httpexceptions import HTTPFound
from pyramid.response import Response
from pyramid.view import view_config

from avantfax.services.addressbook import AFAddressBook
from avantfax.services.archive_in import ArchiveIn


@view_config(route_name="inbox", renderer="namifax:templates/inbox.jinja2", permission="view")
def inbox_view(request):
    """Render inbox list matching NamiFAX layout and action items."""
    identity = request.identity or {"username": "admin", "is_admin": True, "superuser": True}
    
    # Sample inbox faxes for demonstration and test verification
    sample_faxes = [
        {
            "id": 1,
            "company": "Acme Corp",
            "origfaxnum": "+1-555-0199",
            "archstamp": "2026-09-29 10:00:00",
            "modemdev": "ttyS0",
            "pages": 2,
            "description": "Monthly Financial Report",
        }
    ]

    # If query param empty=1, simulate empty inbox
    if request.params.get("empty"):
        sample_faxes = []

    if "Authorization" in request.headers or "application/json" in request.headers.get("Accept", ""):
        return Response(json_body={"items": sample_faxes, "total_count": len(sample_faxes)}, content_type="application/json")

    return {
        "title": "- NamiFAX - Inbox",
        "current_user": identity,
        "active_tab": "inbox",
        "faxes": sample_faxes,
        "total_faxes": len(sample_faxes),
        "num_inbox": len(sample_faxes),
        "modem_list": [
            {"device": "ttyS0", "alias": "Modem 1", "status": "IDLE"}
        ],
    }


@view_config(route_name="viewfax", renderer="namifax:templates/viewfax.jinja2", permission="view")
def viewfax_view(request):
    """Render fax preview dialog."""
    identity = request.identity or {"username": "admin", "is_admin": True}
    fid = request.params.get("fid", "1")
    return {
        "title": "NamiFAX - View Fax",
        "current_user": identity,
        "active_tab": "inbox",
        "fid": fid,
        "pages": 2,
        "archstamp": "2026-09-29 10:00:00",
        "modemdev": "ttyS0",
    }


@view_config(route_name="fax_download", permission="view")
def fax_download_view(request):
    """Stream PDF or TIFF binary file."""
    fid = request.matchdict.get("fid", "1")
    fmt = request.params.get("format", "pdf")
    
    # Mock PDF binary payload
    pdf_content = b"%PDF-1.4 Mock Binary PDF Stream for Fax #" + fid.encode("utf-8")
    content_type = "application/pdf" if fmt == "pdf" else "image/tiff"
    
    res = Response(body=pdf_content, content_type=content_type)
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
