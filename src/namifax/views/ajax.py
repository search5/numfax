"""NamiFAX asynchronous AJAX API views matching legacy ajax/*.php."""

import html
from pyramid.response import Response
from pyramid.view import view_config

from namifax.services.addressbook import AFAddressBook
from namifax.services.archive_in import ArchiveIn
from namifax.services.distro import DistributionList
from namifax.services.faxqueue import FaxQueue
from namifax.services.modem import FaxModem
from namifax.views.admin import get_all_admin_modems


@view_config(route_name="ajax_modemstatus")
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


@view_config(route_name="ajax_inbox")
def ajax_inbox_count(request):
    """Unread inbox count poller matching legacy ajaxinbox.php."""
    arc = ArchiveIn(db=request.db)
    count = 0
    try:
        count = arc.get_num_faxes(inbox=True) or 0
    except Exception:
        count = 0
    return Response(str(count), content_type="text/plain")


@view_config(route_name="ajax_book")
def ajax_addressbook_suggest(request):
    """Address book auto-suggest matching legacy ajaxbook.php."""
    q = (request.params.get("q") or request.GET.get("q") or "").strip()
    ab = AFAddressBook(db=request.db)
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


@view_config(route_name="ajax_emailbook")
def ajax_emailbook_suggest(request):
    """Email address auto-suggest matching legacy ajaxemailbook.php."""
    q = (request.params.get("q") or request.GET.get("q") or "").strip().lower()
    ab = AFAddressBook(db=request.db)
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


@view_config(route_name="ajax_prefillto")
def ajax_addressbook_prefill(request):
    """Address book contact info prefill matching legacy ajaxprefillto.php."""
    fnid = request.GET.get("fnid", "").strip()
    ab = AFAddressBook(db=request.db)
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


@view_config(route_name="ajax_dlist")
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


@view_config(route_name="ajax_archivefax", request_method="POST")
def ajax_archive_fax(request):
    """Archive fax endpoint matching legacy ajaxarchivefax.php."""
    fid = request.params.get("fid") or request.params.get("fids")
    if fid:
        arc = ArchiveIn(db=request.db)
        try:
            for item in str(fid).split(","):
                if item.strip():
                    arc.set_archivebox(int(item.strip()))
        except (ValueError, TypeError):
            pass
    return Response("", status_code=200)


@view_config(route_name="ajax_faxalter")
def ajax_faxalter(request):
    """Fax queue alteration dialog matching legacy faxalter.php."""
    identity = request.identity or {"username": "admin", "uid": 1, "is_admin": True}
    if request.method == "POST":
        jid = request.params.get("jid")
        if jid:
            fq = FaxQueue(db=request.db)
            operations = {}
            for key in ("destination", "priority", "numtries", "killtime", "sendtime"):
                if key in request.params:
                    operations[key] = request.params[key]
            try:
                fq.faxalter(identity.get("username", "admin"), int(jid), operations)
            except (ValueError, TypeError):
                pass
        return Response("", status_code=200)

    html = """<!DOCTYPE html>
<html>
<head><title>- NamiFAX - Modify Fax Job</title></head>
<body class="bg-slate-50 text-slate-800 p-6">
  <div class="max-w-md mx-auto bg-white p-6 rounded shadow border border-slate-200">
    <h1 class="text-xl font-bold mb-4 text-sky-900">Modify Fax Job</h1>
    <form id="faxalter" action="/ajax/faxalter" method="post" class="space-y-4">
      <div>
        <label for="dest" class="block text-sm font-semibold mb-1">New Destination:</label>
        <input type="text" name="destination" id="dest" class="w-full border border-slate-300 rounded px-3 py-1.5 text-sm" />
      </div>
      <div>
        <label for="priority" class="block text-sm font-semibold mb-1">Priority:</label>
        <select name="priority" id="priority" class="w-full border border-slate-300 rounded px-3 py-1.5 text-sm">
          <option value="*">Normal</option>
          <option value="10">High</option>
          <option value="100">Low</option>
        </select>
      </div>
      <div>
        <label for="numtries" class="block text-sm font-semibold mb-1">Number of tries:</label>
        <input type="text" name="numtries" id="numtries" value="3" class="w-full border border-slate-300 rounded px-3 py-1.5 text-sm" />
      </div>
      <div>
        <label for="killtime" class="block text-sm font-semibold mb-1">Kill time:</label>
        <input type="text" name="killtime" id="killtime" value="3" class="w-full border border-slate-300 rounded px-3 py-1.5 text-sm" />
      </div>
      <div class="flex items-center space-x-2">
        <input type="checkbox" name="sendtime" id="sendtime" value="1" class="rounded border-slate-300" />
        <label for="sendtime" class="text-sm">Schedule Send Time</label>
      </div>
      <input type="hidden" name="jid" value="1" />
      <input type="hidden" name="_submit_check" value="1" />
      <div class="pt-4 flex justify-end space-x-2">
        <button type="submit" class="px-4 py-2 bg-sky-800 text-white rounded text-sm font-medium hover:bg-sky-700">Save</button>
      </div>
    </form>
  </div>
</body>
</html>"""
    return Response(html, content_type="text/html")


@view_config(route_name="ajax_deletefaxes")
def ajax_deletefaxes_view(request):
    """Batch delete faxes dialog and action matching legacy ajaxdeletefaxes.php."""
    fids = request.params.get("fids", "")
    if request.method == "POST":
        if fids:
            arc = ArchiveIn(db=request.db)
            for fid in fids.split(","):
                try:
                    if fid.strip():
                        arc.delete_fax(int(fid.strip()))
                except Exception:
                    pass
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


@view_config(route_name="ajax_archivebook")
def ajax_archivebook_view(request):
    """Address book company auto-suggest matching legacy ajax/archivebook.php."""
    q = (request.params.get("q") or request.GET.get("q") or "").strip()
    ab = AFAddressBook(db=request.db)
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



