"""NamiFAX asynchronous AJAX API views matching legacy ajax/*.php."""

import html
from pyramid.httpexceptions import HTTPFound, HTTPForbidden
from pyramid.response import Response
from pyramid.view import view_config

from namifax.i18n import _
from namifax.services.addressbook import AFAddressBook
from namifax.services.archive_in import ArchiveIn
from namifax.services.distro import DistributionList
from namifax.services.faxqueue import FaxQueue
from namifax.services.modem import FaxModem
from namifax.views.admin import get_all_admin_modems
from namifax.views.fax_rights import fax_access, load_fax


@view_config(route_name="ajax_modemstatus", permission="view")
def ajax_modem_status(request):
    """Real-time modem status poller matching legacy ajaxmodemstatus.php."""
    modems = get_all_admin_modems(request.dbsession)
    rows_xml = []
    try:
        fm = FaxModem(db=request.dbsession)
        for m in modems:
            dev = m.get("device", "ttyS0")
            status_info = m.get("status", "Idle")
            if fm.load_device(dev):
                st = fm.get_status()
                status_info = st.get("status", status_info)
                cls_info = st.get("class", "2.0")
            else:
                cls_info = "2.0"
            rows_xml.append(
                f"  <row>\n"
                f"    <modem>{html.escape(str(dev))}</modem>\n"
                f"    <status>{html.escape(str(status_info))}</status>\n"
                f"    <class>{html.escape(str(cls_info))}</class>\n"
                f"  </row>"
            )
    except Exception:
        pass

    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n<response>\n' + "\n".join(rows_xml) + ("\n" if rows_xml else "") + "</response>"
    return Response(xml_content, content_type="text/xml")


@view_config(route_name="ajax_inbox", permission="view")
def ajax_inbox_count(request):
    """Unread inbox count poller matching legacy ajaxinbox.php."""
    arc = ArchiveIn(db=request.dbsession)
    count = 0
    try:
        access = fax_access(request)
        count = arc.get_num_faxes(access.devices, access.categories, access.did_routing) or 0
    except Exception:
        count = 0
    return Response(str(count), content_type="text/plain")


@view_config(route_name="ajax_book", permission="view")
def ajax_addressbook_suggest(request):
    """Address book auto-suggest matching legacy ajaxbook.php."""
    q = (request.params.get("q") or request.GET.get("q") or "").strip()
    ab = AFAddressBook(db=request.dbsession)
    rows_xml = []

    try:
        companies = ab.search_companies(q) if q else ab.get_companies()
        if companies:
            for c in companies:
                cid = c.get("ab_id") or c.get("abook_id") or 1
                cname = c.get("company", "")
                faxnum = c.get("faxnum") or c.get("faxnumber") or ""
                label = f"{cname} - {faxnum}" if faxnum else cname
                rows_xml.append(
                    f"  <row>\n"
                    f"    <company>{html.escape(label)}</company>\n"
                    f"    <cid>{cid}</cid>\n"
                    f"    <faxnum>{html.escape(str(faxnum))}</faxnum>\n"
                    f"    <fnid>{cid}</fnid>\n"
                    f"  </row>"
                )
    except Exception:
        pass

    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n<response>\n' + "\n".join(rows_xml) + ("\n" if rows_xml else "") + "</response>"
    return Response(xml_content, content_type="text/xml")


@view_config(route_name="ajax_emailbook", permission="view")
def ajax_emailbook_suggest(request):
    """Email address auto-suggest matching legacy ajaxemailbook.php."""
    q = (request.params.get("q") or request.GET.get("q") or "").strip().lower()
    ab = AFAddressBook(db=request.dbsession)
    rows_xml = []

    try:
        contacts = ab.get_contacts()
        if contacts:
            for eid, cstr in contacts.items():
                email = cstr.split("<")[1].replace(">", "").strip() if "<" in cstr else cstr
                if not q or q in email.lower() or q in cstr.lower():
                    rows_xml.append(
                        f"  <row>\n"
                        f"    <id>{eid}</id>\n"
                        f"    <email>{html.escape(email)}</email>\n"
                        f"  </row>"
                    )
    except Exception:
        pass

    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n<response>\n' + "\n".join(rows_xml) + ("\n" if rows_xml else "") + "</response>"
    return Response(xml_content, content_type="text/xml")


@view_config(route_name="ajax_prefillto", permission="view")
def ajax_addressbook_prefill(request):
    """Address book contact info prefill matching legacy ajaxprefillto.php."""
    fnid = request.GET.get("fnid", "").strip()
    ab = AFAddressBook(db=request.dbsession)
    to_company = ""
    to_person = ""
    to_address = ""
    to_zip = ""
    to_city = ""
    to_location = ""
    to_voicenumber = ""

    try:
        if fnid.isdigit():
            fid_int = int(fnid)
            if ab.loadbyfaxnumid(fid_int):
                to_company = ab.get_company() or ""
                to_person = ab.get_to_person() or ""
                to_address = ab.get_to_address() or ""
                to_zip = ab.get_to_zip() or ""
                to_city = ab.get_to_city() or ""
                to_location = ab.get_to_location() or ""
                to_voicenumber = ab.get_to_voicenumber() or ""
            elif ab.loadbycid(fid_int):
                to_company = ab.get_company() or ""
    except Exception:
        pass

    xml_content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<response>\n"
        "  <row>\n"
        f"    <to_company>{html.escape(str(to_company))}</to_company>\n"
        f"    <to_person>{html.escape(str(to_person))}</to_person>\n"
        f"    <to_address>{html.escape(str(to_address))}</to_address>\n"
        f"    <to_zip>{html.escape(str(to_zip))}</to_zip>\n"
        f"    <to_city>{html.escape(str(to_city))}</to_city>\n"
        f"    <to_location>{html.escape(str(to_location))}</to_location>\n"
        f"    <to_voicenumber>{html.escape(str(to_voicenumber))}</to_voicenumber>\n"
        "  </row>\n"
        "</response>"
    )
    return Response(xml_content, content_type="text/xml")


@view_config(route_name="ajax_dlist", permission="view")
def ajax_distrolist_faxes(request):
    """Distribution list fax numbers matching legacy ajaxdlist.php."""
    dl_id = request.GET.get("dl_id", "").strip()
    dl = DistributionList(db=request.dbsession)
    faxes_str = ""

    try:
        if dl_id.isdigit() and dl.load_list(int(dl_id)):
            entries = dl.list_entries()
            if entries:
                faxes_str = "; ".join(entries)
    except Exception:
        pass

    return Response(faxes_str, content_type="text/plain")


@view_config(route_name="ajax_archivefax", request_method="POST", permission="view")
def ajax_archive_fax(request):
    """Archive fax endpoint matching legacy ajaxarchivefax.php."""
    fid = request.params.get("fid") or request.params.get("fids")
    if fid:
        arc = ArchiveIn(db=request.dbsession)
        for item in str(fid).split(","):
            if item.strip() and load_fax(request, arc, item.strip(), action="ajaxarchivefax"):
                arc.set_archivebox(int(item.strip()))
    return Response("", status_code=200)


@view_config(route_name="ajax_faxalter", renderer="namifax:templates/faxalter.jinja2", permission="view")
def ajax_faxalter(request):
    """Modify or resubmit a queued fax job (the original ajax/faxalter.php).

    The fields become faxalter operations in the original's order. The job is altered in the name of the signed-in user;
    only a superuser may name another owner (the original took any owner from the request, so anybody could alter any job).
    """
    access = fax_access(request)
    params = request.POST if request.method == "POST" else request.params
    resubmit = bool(params.get("resubmit") or params.get("r"))
    jid = (params.get("jid") or "").strip()
    owner = (params.get("owner") or "").strip() if access.superuser else ""
    owner = owner or access.username or (request.identity or {}).get("username", "")

    modems = FaxModem(db=request.dbsession)
    devices = (access.configured_modems if access.superuser else access.modems) or []
    modem_list = []
    for device in devices:
        if modems.load_device(device):
            modem_list.append((device, modems.get_alias() or device))

    def text(name: str, default: str = "") -> str:
        return (params.get(name) or default).strip()

    values = {"jid": jid, "owner": owner, "resubmit": "1" if resubmit else "", "destination": text("destination"),
              "priority": text("priority", "*"), "modem": text("modem"), "numtries": text("numtries"),
              "killtime": text("killtime", "3" if resubmit and request.method != "POST" else ""),
              "killtime_unit": text("killtime_unit", "hours"), "sendnow": bool(text("sendnow")),
              "sendtime": bool(text("sendtime")), "sendtimeHour": text("sendtimeHour"), "sendtimeMin": text("sendtimeMin")}

    def page(error=None):
        return {"title": "- NamiFAX - Modify Fax Job", "values": values, "error": error, "modem_list": modem_list,
                "priority_list": ["*"] + [str(n) for n in range(0, 255, 10)],
                "hours": [f"{n:02d}" for n in range(24)], "minutes": [f"{n:02d}" for n in range(60)]}

    if request.method != "POST":
        return page()

    if not (jid.isdigit() and (not values["killtime"] or values["killtime"].isdigit())
            and (not values["numtries"] or values["numtries"].isdigit())):
        return page(_("Please enter a valid number."))

    operations: dict = {}
    if values["destination"]:
        operations["destination"] = values["destination"]
    if values["numtries"]:
        operations["tries"] = values["numtries"]
    if values["modem"]:
        operations["device"] = values["modem"]
    if values["priority"] != "*":
        operations["priority"] = values["priority"]
    if values["sendtime"] and values["sendtimeHour"] and values["sendtimeMin"]:
        operations["sendtime"] = f"{values['sendtimeHour']}:{values['sendtimeMin']}"
    if values["killtime"]:
        operations["killtime"] = f"now + {values['killtime']} {values['killtime_unit']}"
    if values["sendnow"]:
        operations["sendtime"] = "now"
    if resubmit:
        operations["resubmit"] = True

    FaxQueue(db=request.dbsession).faxalter(owner, int(jid), operations)
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return Response("", status_code=200)
    return HTTPFound(location=request.route_url("outbox"))


@view_config(route_name="ajax_deletefaxes", permission="view")
def ajax_deletefaxes_view(request):
    """Batch delete faxes dialog and action matching legacy ajaxdeletefaxes.php."""
    fids = request.params.get("fids", "")
    access = fax_access(request)
    if not (access.can_del or access.superuser):
        raise HTTPForbidden("You may not delete faxes.")
    if request.method == "POST":
        if fids:
            arc = ArchiveIn(db=request.dbsession)
            for fid in fids.split(","):
                if fid.strip() and load_fax(request, arc, fid.strip(), action="ajaxdeletefaxes", delete=True):
                    arc.delete_fax()
        return Response("", status_code=200)

    html = f"""<!DOCTYPE html>
<html>
<head><title>Delete</title></head>
<body class="bg-slate-50 p-4 text-xs">
  <div class="max-w-sm mx-auto bg-white p-4 rounded border border-slate-300 text-center">
    <p class="font-semibold text-slate-700 mb-4">Delete selected faxes?</p>
    <form action="/ajax/deletefaxes" method="post">
      <input type="hidden" name="fids" value="{fids}" />
      <input type="hidden" name="_submit_check" value="1" />
      <div class="flex justify-center space-x-2">
        <button type="button" onclick="window.close()" class="px-3 py-1 bg-slate-200 text-slate-700 rounded">Cancel</button>
        <button type="submit" class="px-4 py-1 bg-rose-700 text-white rounded">Delete</button>
      </div>
    </form>
  </div>
</body>
</html>"""
    return Response(html, content_type="text/html")


@view_config(route_name="ajax_archivebook", permission="view")
def ajax_archivebook_view(request):
    """Address book company auto-suggest matching legacy ajax/archivebook.php."""
    q = (request.params.get("q") or request.GET.get("q") or "").strip()
    ab = AFAddressBook(db=request.dbsession)
    rows_xml = []

    try:
        companies = ab.search_companies(q) if q else ab.get_companies()
        if companies:
            for c in companies:
                cid = c.get("ab_id") or c.get("abook_id") or 1
                cname = c.get("company", "")
                rows_xml.append(
                    f"  <row>\n"
                    f"    <company>{html.escape(cname)}</company>\n"
                    f"    <cid>{cid}</cid>\n"
                    f"  </row>"
                )
    except Exception:
        pass

    if rows_xml:
        xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n<response>\n' + "\n".join(rows_xml) + "\n</response>"
    else:
        xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n<response></response>'
    return Response(xml_content, content_type="text/xml")



