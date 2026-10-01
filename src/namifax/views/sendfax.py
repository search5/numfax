"""NamiFAX SendFax View matching legacy NamiFAX behavior."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from typing import Any

from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config

from namifax.services.addressbook import RESERVED_FAX_NUM, AFAddressBook
from namifax.services.archive_in import ArchiveIn
from namifax.services.covers import Covers
from namifax.services.sendfax_command import NothingToSend, Sender, SendRequest, build_plan
from namifax.services.user_account import AFUserAccount
from namifax.views.fax_rights import load_fax
from namifax.views.admin import get_all_admin_modems


def _images_dir() -> str:
    return os.path.join(os.environ.get("AVANTFAX_INSTALLDIR", "/var/www/avantfax"), "images")


def _tmp_dir() -> str:
    return tempfile.gettempdir().rstrip("/") + "/"


def _faxcover_command() -> list[str]:
    configured = os.environ.get("NAMIFAX_FAXCOVER")
    return [configured] if configured else [sys.executable, "-m", "namifax.cli.faxcover"]


def _simulation_wanted() -> bool:
    flag = os.environ.get("NAMIFAX_QUEUE_SIMULATION")
    if flag is not None:
        return flag.lower() in ("1", "true", "yes")
    return bool(os.environ.get("PYTEST_CURRENT_TEST")) or not os.path.exists("/var/spool/hylafax")


def dispatch_sendfax(send: SendRequest, sender: Sender) -> dict[str, Any]:
    """Run sendfax (and faxcover for a cover page without a file) for the form, or simulate when HylaFAX is absent."""
    try:
        plan = build_plan(send, sender, images_dir=_images_dir(), tmp_dir=_tmp_dir(),
                          default_tsi=os.environ.get("DEFAULT_TSI_ID", ""))
    except NothingToSend:
        return {"success": False, "error": "Select a file to send, or ask for a cover page."}

    sendfax_bin = shutil.which("sendfax")
    if not sendfax_bin:
        if _simulation_wanted():
            return {"success": True, "jobid": str(uuid.uuid4().int)[:6], "destination": send.destinations.strip(),
                    "files_count": len(send.files), "simulated": True}
        return {"success": False, "error": "HylaFAX sendfax binary not found on host system.", "simulated": False}

    binaries = {"sendfax": [sendfax_bin], "faxcover": _faxcover_command()}
    try:
        for path, content in plan.files_to_write.items():
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(content)
        output = ""
        for step in plan.steps:
            argv = [*binaries[step.argv[0]], *step.argv[1:]]
            if step.stdout_to:
                with open(step.stdout_to, "wb") as sink:
                    result = subprocess.run(argv, stdout=sink, stderr=subprocess.PIPE, check=False)
                output = result.stderr.decode(errors="replace")
            else:
                result = subprocess.run(argv, capture_output=True, text=True, check=False)
                output = (result.stdout or "") + (result.stderr or "")
            if result.returncode != 0:
                return {"success": False, "error": output.strip() or f"{step.argv[0]} failed"}
        match = re.search(r"request id is (\d+)", output)
        return {"success": True, "output": output, "jobid": match.group(1) if match else None}
    except OSError as exc:
        return {"success": False, "error": str(exc)}
    finally:
        for path in [*plan.files_to_write, *plan.cleanup]:
            try:
                os.remove(path)
            except OSError:
                pass


def _sender_number(request, fax: ArchiveIn) -> str:
    """The number to answer: the address book's number for the fax, else the number it came from (blank if unusable)."""
    number = None
    book = AFAddressBook(db=request.dbsession)
    if fax.get_faxnumid() and book.loadbyfaxnumid(fax.get_faxnumid()):
        number = book.get_faxnumber()
    number = number or fax.get_origfaxnum() or ""
    return number if any(c.isdigit() for c in number) and number != RESERVED_FAX_NUM else ""


def _account(request) -> tuple[Sender, dict[str, Any]]:
    """The signed-in user as the sender of the fax, and their account values."""
    username = str((request.identity or {}).get("username") or "")
    account = AFUserAccount(db=request.dbsession)
    if not username or not account.load_username(username):
        return Sender(username=username), {}
    d = account.dbdata
    return Sender(name=d.get("name") or "", username=username, email=d.get("email") or "", company=d.get("from_company") or "",
                  location=d.get("from_location") or "", voicenumber=d.get("from_voicenumber") or "",
                  faxnumber=d.get("from_faxnumber") or ""), d


def _covers(request, account: dict[str, Any]) -> tuple[list[tuple[str, str]], str]:
    """(file, title) of every cover page, and the file of the user's own choice (the first one without)."""
    covers = Covers(db=request.dbsession)
    options, chosen = [], ""
    for file in covers.get_covers() or []:
        if covers.load_cover(file):
            options.append((file, covers.get_title() or file))
            if account.get("coverpage_id") and covers.get_cover_id() == account.get("coverpage_id"):
                chosen = file
    return options, chosen or (options[0][0] if options else "")


def _send_request(params, files: list[str]) -> SendRequest:
    def text(name: str) -> str:
        return (params.get(name) or "").strip()

    return SendRequest(
        destinations=text("faxnumber") or text("destinations"), files=files, modem=text("modem") or None,
        to_person=text("to_person"), to_company=text("to_company"), regarding=text("regarding"), comments=text("comments"),
        to_location=text("to_location"), to_voicenumber=text("to_voicenumber"), to_address=text("to_address"),
        to_zip=text("to_zip"), to_city=text("to_city"), tsi=text("user_tsi"), coverpage=bool(text("coverpage")),
        whichcover=text("whichcover"), notify_requeue=bool(text("notify_requeue")), priority=text("priority") or "*",
        numtries=text("numtries"), killtime=text("killtime"), killtime_unit=text("killtime_unit") or "hours",
        sendtime=bool(text("sendtime")), sendtime_hour=text("sendtimeHour"), sendtime_min=text("sendtimeMin"))


@view_config(route_name="sendfax", renderer="namifax:templates/sendfax.jinja2", permission="send_fax")
def sendfax_view(request):
    """Render the Send Fax form, or submit it to HylaFAX (the original sendfax.php / refax.php)."""
    identity = request.identity or {"username": "admin", "is_admin": True}
    sender, account = _account(request)
    cover_list, default_cover = _covers(request, account)

    def page(form_data, error=None, original_fid=None):
        return {
            "title": "- NamiFAX - Send Fax", "current_user": identity, "active_tab": "sendfax", "error": error,
            "form_data": form_data, "modem_list": get_all_admin_modems(request.dbsession), "cover_list": cover_list,
            "default_cover": default_cover, "original_fid": original_fid,
            "priority_list": ["*"] + [str(n) for n in range(0, 255, 10)],
            "hours": [f"{n:02d}" for n in range(24)], "minutes": [f"{n:02d}" for n in range(60)],
            "default_tsi": account.get("user_tsi") or "",
        }

    # "Reply to fax": the fax being answered must exist and the user must have the right to it, else the plain page
    original = None
    refax = request.params.get("refax")
    if refax:
        original = ArchiveIn(db=request.dbsession)
        if not load_fax(request, original, refax, action="refax"):
            return HTTPFound(location=request.route_url("sendfax"))
    original_fid = original.get_fid() if original is not None else None

    if request.method != "POST":
        form = {"faxnumber": _sender_number(request, original)} if original is not None else {}
        return page(form, original_fid=original_fid)

    params = request.params
    if not (params.get("faxnumber") or params.get("destinations") or "").strip():
        return page(params, "Fax number is required", original_fid)

    files: list[str] = [original.get_pdfpath()] if original is not None and original.get_pdfpath() else []
    uploaded: list[str] = []
    for item in request.POST.getall("file"):
        if hasattr(item, "file") and getattr(item, "filename", ""):
            dest_path = os.path.join(tempfile.gettempdir(), f"sendfax_{uuid.uuid4().hex[:8]}_{os.path.basename(item.filename)}")
            with open(dest_path, "wb") as out:
                shutil.copyfileobj(item.file, out)
            uploaded.append(dest_path)
    try:
        result = dispatch_sendfax(_send_request(params, files + uploaded), sender)
    finally:
        for path in uploaded:
            try:
                os.remove(path)
            except OSError:
                pass
    if not result.get("success"):
        return page(params, result.get("error", "Failed to dispatch fax"), original_fid)
    return HTTPFound(location=request.route_url("outbox"))
