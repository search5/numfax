"""NamiFAX Interaction Modals and Dialog Views matching legacy NamiFAX popups."""

from __future__ import annotations

from pyramid.view import view_config

from avantfax.services.addressbook import AFAddressBook
from avantfax.services.archive_in import ArchiveIn
from avantfax.services.faxqueue import FaxQueue
from avantfax.services.mailer import Mailer


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
            arc = ArchiveIn()
            pdf_path = None
            thumb_path = None
            try:
                if arc.load_fax(int(fid)):
                    pdf_path = arc.get_pdfpath()
                    thumb_path = arc.get_thumbnail()
            except (ValueError, TypeError):
                pass

            mailer = Mailer()
            sent = mailer.send_mail(
                to=emails,
                subject=subject,
                message=msg,
                attachment=pdf_path,
                thumbnail=thumb_path,
            )
            if sent:
                ab = AFAddressBook()
                ab.create_contacts(emails)
                message = "Email sent successfully"
            else:
                error = mailer.get_error() or "Failed to send email"

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

    if request.method == "POST":
        myselect = request.params.get("myselect")
        regexp = request.params.get("regexp", "").strip()
        ab = AFAddressBook()
        arc = ArchiveIn()

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

    return {
        "title": "- NamiFAX - Assign Company",
        "current_user": identity,
        "fid": fid,
        "companies": [{"id": 1, "name": "Acme Global"}, {"id": 2, "name": "Initech Corp"}],
        "message": message,
    }


@view_config(route_name="modal_note", renderer="namifax:templates/modal_note.jinja2", permission="view")
def modal_note_view(request):
    """Render add note dialog and update fax description."""
    identity = request.identity or {"username": "admin", "uid": 1, "is_admin": True}
    fid = request.params.get("fid", "1")
    desc = request.params.get("description", "Reviewed and verified by operator.")
    message = None

    if request.method == "POST":
        desc = request.params.get("description", "").strip()
        arc = ArchiveIn()
        try:
            if fid and arc.load_fax(int(fid)):
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

    if request.method == "POST":
        arc = ArchiveIn()
        try:
            if fid and arc.delete_fax(int(fid)):
                status = "deleted"
        except (ValueError, TypeError):
            pass

    return {
        "title": "- NamiFAX - Delete Fax",
        "current_user": identity,
        "fid": fid,
        "status": status,
    }


@view_config(route_name="modal_refax", renderer="namifax:templates/modal_refax.jinja2", permission="view")
def modal_refax_view(request):
    """Render reply to fax / resend dialog and create FaxQueue job."""
    identity = request.identity or {"username": "admin", "uid": 1, "is_admin": True}
    fid = request.params.get("fid", "1")
    destinations = request.params.get("destinations", "+1-555-0199")
    regarding = request.params.get("regarding", "Re: Document Transmission")
    comments = request.params.get("comments", "Resending previous transmission.")
    message = None

    if request.method == "POST":
        destinations = request.params.get("destinations", "").strip()
        regarding = request.params.get("regarding", "").strip()
        comments = request.params.get("comments", "").strip()

        if destinations:
            fq = FaxQueue()
            jid = fq.create_job(
                destinations=destinations,
                regarding=regarding,
                comments=comments,
                user=identity.get("username", "avantfax"),
            )
            if jid:
                message = f"Fax queued for sending (Job ID: {jid})"

    return {
        "title": "- NamiFAX - Reply to Fax",
        "current_user": identity,
        "fid": fid,
        "destinations": destinations,
        "regarding": regarding,
        "comments": comments,
        "message": message,
    }


@view_config(route_name="modal_txreport", renderer="namifax:templates/modal_txreport.jinja2", permission="view")
def modal_txreport_view(request):
    """Render transmission report dialog."""
    identity = request.identity or {"username": "admin", "uid": 1, "is_admin": True}
    return {
        "title": "- NamiFAX - Transmission Report",
        "current_user": identity,
        "fid": request.params.get("fid", "1"),
        "company": "Acme Global",
        "date": "2026-09-29 10:15:00",
        "pages": 2,
    }
