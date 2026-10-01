"""NamiFAX Interaction Modals and Dialog Views matching legacy NamiFAX popups."""

from __future__ import annotations

from pyramid.csrf import check_csrf_token
from pyramid.httpexceptions import HTTPFound, HTTPForbidden
from pyramid.view import view_config

from namifax.i18n import _
from namifax.services.addressbook import AFAddressBook
from namifax.services.archive_in import ArchiveIn
from namifax.services.faxqueue import FaxQueue
from namifax.common.helpers import send_mail
from namifax.views.fax_rights import fax_access, load_fax


@view_config(route_name="modal_email", renderer="namifax:templates/modal_email.jinja2", permission="view")
def modal_email_view(request):
    """Render send fax via email modal dialog and handle email dispatch."""
    identity = request.identity or {"username": "admin", "uid": 1, "is_admin": True}
    fid = request.params.get("fid", "1")
    emails = request.params.get("emails", "")
    subject = request.params.get("subject", f"Forwarded Fax Document #{fid}")
    msg = request.params.get("msg", "Please find attached the requested facsimile transmission.")
    message = None
    error = None

    if request.method == "POST":
        emails = request.params.get("emails", "").strip()
        subject = request.params.get("subject", "").strip() or f"Forwarded Fax Document #{fid}"
        msg = request.params.get("msg", "").strip()

        if emails:
            arc = ArchiveIn(db=request.dbsession)
            pdf_path = None
            thumb_path = None
            try:
                if load_fax(request, arc, fid, action="email"):
                    pdf_path = arc.get_pdfpath()
                    thumb_path = arc.get_thumbnail()
            except (ValueError, TypeError):
                pass

            sent = send_mail(
                emails,
                identity.get("email"),
                subject,
                msg,
                file=pdf_path,
                altname=request.params.get("filename") or None,
                embedd=thumb_path,
                session=request.dbsession,
            )
            if sent:
                ab = AFAddressBook(db=request.dbsession)
                ab.create_contacts(emails)
                message = "Email sent successfully"
            else:
                error = "Failed to send email"

    return {
        "title": "- NamiFAX - Send Fax via Email",
        "current_user": identity,
        "fid": fid,
        "emails": emails,
        "subject": subject,
        "msg": msg,
        "message": message,
        "error": error,
    }


@view_config(route_name="modal_assign", renderer="namifax:templates/modal_assign.jinja2", permission="view")
def modal_assign_view(request):
    """Render assign company name dialog and persist company mapping."""
    identity = request.identity or {"username": "admin", "uid": 1, "is_admin": True}
    fid = request.params.get("fid", "1")
    abook_id = request.params.get("abook_id", "1")
    message = None

    ab = AFAddressBook(db=request.dbsession)
    if request.method == "POST":
        myselect = request.params.get("myselect")
        regexp = request.params.get("regexp", "").strip()
        arc = ArchiveIn(db=request.dbsession)

        if myselect:
            try:
                target_cid = int(myselect)
                src_cid = int(abook_id) if abook_id else 1
                if ab.loadbycid(src_cid):
                    oldcid = ab.get_companyid()
                    if ab.reassign(target_cid):
                        arc.reassign(oldcid, target_cid)
                        message = "Company reassigned successfully"
            except (ValueError, TypeError):
                pass
        elif regexp:
            ab.set_company(regexp)
            message = "Company updated successfully"

    company_records = []
    try:
        raw_cos = ab.get_companies() or []
        for r in raw_cos:
            cid = r.get("ab_id") or r.get("abook_id") or r.get("id")
            cname = r.get("company") or r.get("company_name") or r.get("name")
            if cid and cname:
                company_records.append({"id": cid, "name": cname})
    except Exception:
        pass

    return {
        "title": "- NamiFAX - Assign Company",
        "current_user": identity,
        "fid": fid,
        "companies": company_records,
        "message": message,
    }


@view_config(route_name="assignx", renderer="namifax:templates/assignx.jinja2", permission="view")
def assignx_view(request):
    """Name the sender of a fax nobody knows (the original assignx.php): pick an existing company or type a new one.

    The fax gets the company (its number link is cleared, as the original did). Unlike the original the user needs the
    right to the fax, and the POST carries the session's CSRF token.
    """
    fid = (request.params.get("fid") or "").strip()
    arc = ArchiveIn(db=request.dbsession)
    if not fid.isdigit() or not load_fax(request, arc, fid, action="assignx"):
        return HTTPFound(location=request.route_url("inbox"))

    book = AFAddressBook(db=request.dbsession)
    error = None
    if request.method == "POST":
        check_csrf_token(request)
        chosen = (request.POST.get("abook_id") or "").strip()
        name = (request.POST.get("regexp") or "").strip()
        cid = None
        if chosen.isdigit() and book.loadbycid(int(chosen)):
            cid = int(chosen)
        elif name:
            if book.create(name):
                cid = book.get_companyid()
            else:
                error = book.get_error()
        else:
            error = _("Please enter a company name")
        if cid:
            arc.set_faxnumid(0)                       # no longer tied to the reserved number
            arc.set_companyid(cid)
            return HTTPFound(location=request.route_url("inbox"))

    companies = [(c.get("abook_id"), c.get("company")) for c in book.get_companies() or [] if c.get("company")]
    return {"title": "- NamiFAX - Name the sender", "fid": fid, "companies": companies, "error": error,
            "origfaxnum": arc.get_origfaxnum() or "", "csrf_token": request.session.get_csrf_token()}


@view_config(route_name="modal_note", renderer="namifax:templates/modal_note.jinja2", permission="view")
def modal_note_view(request):
    """Render add note dialog and update fax description."""
    identity = request.identity or {"username": "admin", "uid": 1, "is_admin": True}
    fid = request.params.get("fid", "1")
    desc = request.params.get("description", "Reviewed and verified by operator.")
    message = None

    if request.method == "POST":
        desc = request.params.get("description", "").strip()
        arc = ArchiveIn(db=request.dbsession)
        try:
            if fid and load_fax(request, arc, fid, action="set_note"):
                arc.set_note(description=desc, category=None, userid=identity.get("uid", 1))
                message = "Note saved successfully"
        except (ValueError, TypeError):
            pass

    return {
        "title": "- NamiFAX - Add Note",
        "current_user": identity,
        "fid": fid,
        "description": desc,
        "message": message,
    }


@view_config(route_name="modal_delete", renderer="namifax:templates/modal_delete.jinja2", permission="view")
def modal_delete_view(request):
    """Render delete fax confirmation dialog and delete fax record and assets."""
    identity = request.identity or {"username": "admin", "uid": 1, "is_admin": True}
    fid = request.params.get("fid", "1")
    status = None

    if not fax_access(request).can_del and not fax_access(request).superuser:
        raise HTTPForbidden("You may not delete faxes.")

    if request.method == "POST":
        arc = ArchiveIn(db=request.dbsession)
        try:
            if fid and load_fax(request, arc, fid, action="delete", delete=True) and arc.delete_fax():
                status = "deleted"
        except (ValueError, TypeError):
            pass

    return {
        "title": "- NamiFAX - Delete Fax",
        "current_user": identity,
        "fid": fid,
        "status": status,
    }


@view_config(route_name="modal_refax", permission="view")
def modal_refax_view(request):
    """The original's refax.php?fid=N: the reply to a received fax is the Send Fax page (``sendfax?refax=N``)."""
    fid = (request.params.get("fid") or "").strip()
    if fid.isdigit():
        return HTTPFound(location=request.route_url("sendfax", _query={"refax": fid}))
    return HTTPFound(location=request.route_url("sendfax"))


@view_config(route_name="modal_txreport", renderer="namifax:templates/modal_txreport.jinja2", permission="view")
def modal_txreport_view(request):
    """Render transmission report dialog."""
    identity = request.identity or {"username": "admin", "uid": 1, "is_admin": True}
    fid = request.params.get("fid", "1")
    company = ""
    date_val = ""
    pages_val = 0

    arc = ArchiveIn(db=request.dbsession)
    try:
        if fid and str(fid).isdigit() and load_fax(request, arc, fid, action="txreport"):
            date_val = arc.get_archstamp() or ""
            pages_val = arc.get_pages() or 0
            cid = arc.get_companyid()
            if cid:
                ab = AFAddressBook(db=request.dbsession)
                if ab.loadbycid(cid):
                    company = ab.get_company() or ""
            elif arc.get_origfaxnum():
                company = arc.get_origfaxnum()
    except Exception:
        pass

    return {
        "title": "- NamiFAX - Transmission Report",
        "current_user": identity,
        "fid": fid,
        "company": company,
        "date": date_val,
        "pages": pages_val,
    }
