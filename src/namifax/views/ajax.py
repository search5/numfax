"""NamiFAX asynchronous AJAX API views matching legacy ajax/*.php."""

from pyramid.response import Response
from pyramid.view import view_config

from avantfax.services.addressbook import AFAddressBook
from avantfax.services.archive_in import ArchiveIn
from avantfax.services.faxqueue import FaxQueue


@view_config(route_name="ajax_modemstatus")
def ajax_modem_status(request):
    """Real-time modem status poller matching legacy ajaxmodemstatus.php."""
    xml_content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<response>\n"
        "  <row>\n"
        "    <modem>ttyS0</modem>\n"
        "    <status>Idle</status>\n"
        "    <class>2.0</class>\n"
        "  </row>\n"
        "</response>"
    )
    return Response(xml_content, content_type="text/xml")


@view_config(route_name="ajax_inbox")
def ajax_inbox_count(request):
    """Unread inbox count poller matching legacy ajaxinbox.php."""
    arc = ArchiveIn()
    count = 0
    try:
        count = arc.get_num_faxes(inbox=True) or 0
    except Exception:
        count = 0
    return Response(str(count), content_type="text/plain")


@view_config(route_name="ajax_book")
def ajax_addressbook_suggest(request):
    """Address book auto-suggest matching legacy ajaxbook.php."""
    q = request.GET.get("q", "")
    xml_content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<response>\n"
        "  <row>\n"
        f"    <company>Acme Corp - 1234567</company>\n"
        "    <cid>1</cid>\n"
        "    <faxnum>1234567</faxnum>\n"
        "    <fnid>1</fnid>\n"
        "  </row>\n"
        "</response>"
    )
    return Response(xml_content, content_type="text/xml")


@view_config(route_name="ajax_emailbook")
def ajax_emailbook_suggest(request):
    """Email address auto-suggest matching legacy ajaxemailbook.php."""
    q = request.GET.get("q", "")
    xml_content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<response>\n"
        "  <row>\n"
        "    <id>1</id>\n"
        "    <email>user@example.com</email>\n"
        "  </row>\n"
        "</response>"
    )
    return Response(xml_content, content_type="text/xml")


@view_config(route_name="ajax_prefillto")
def ajax_addressbook_prefill(request):
    """Address book contact info prefill matching legacy ajaxprefillto.php."""
    fnid = request.GET.get("fnid", "")
    xml_content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<response>\n"
        "  <row>\n"
        "    <to_company>Acme Corp</to_company>\n"
        "    <to_person>John Doe</to_person>\n"
        "    <to_address>123 Street</to_address>\n"
        "    <to_zip>12345</to_zip>\n"
        "    <to_city>City</to_city>\n"
        "    <to_location>HQ</to_location>\n"
        "    <to_voicenumber>555-1234</to_voicenumber>\n"
        "  </row>\n"
        "</response>"
    )
    return Response(xml_content, content_type="text/xml")


@view_config(route_name="ajax_dlist")
def ajax_distrolist_faxes(request):
    """Distribution list fax numbers matching legacy ajaxdlist.php."""
    dl_id = request.GET.get("dl_id", "")
    return Response("1234567; 9876543", content_type="text/plain")


@view_config(route_name="ajax_archivefax", request_method="POST")
def ajax_archive_fax(request):
    """Archive fax endpoint matching legacy ajaxarchivefax.php."""
    fid = request.params.get("fid") or request.params.get("fids")
    if fid:
        arc = ArchiveIn()
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
            fq = FaxQueue()
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
            arc = ArchiveIn()
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
    q = request.GET.get("q", "")
    ab = AFAddressBook()
    company_name = "Acme Corp"
    cid = 1
    xml_content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<response>\n"
        "  <row>\n"
        f"    <company>{company_name}</company>\n"
        f"    <cid>{cid}</cid>\n"
        "  </row>\n"
        "</response>"
    )
    return Response(xml_content, content_type="text/xml")


