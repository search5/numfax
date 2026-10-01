"""NamiFAX popup helper dialogs and vCard upload views matching legacy NamiFAX."""

import html
from pyramid.httpexceptions import HTTPFound
from pyramid.response import Response
from pyramid.view import view_config

from namifax.services.addressbook import AFAddressBook
from namifax.services.categories import FaxPDFCategory
from namifax.services.distro import DistributionList


@view_config(route_name="popup_distrolist_helper", renderer="namifax:templates/distrolist_helper.jinja2", permission="view")
def popup_distrolist_helper(request):
    """Add address-book fax numbers to a distribution list (the original distrolist_helper.php).

    The search box lists the fax numbers of the companies that match; the chosen ones are added as ``<id>|<number>``.
    """
    import os

    dl_id = (request.params.get("dl_id") or "").strip()
    dl = DistributionList(db=request.dbsession)
    if not dl_id.isdigit() or not dl.load_list(int(dl_id)):
        raise HTTPFound(location=request.route_url("distrolist"))

    added = False
    error = None
    if request.method == "POST":
        chosen = request.POST.getall("myselect[]") or request.POST.getall("myselect")
        who = (request.identity or {}).get("user_id") or (request.identity or {}).get("uid")
        dl.set_moduser(int(who) if who else None)
        if dl.add_entries([c for c in chosen if c.split("|", 1)[0].isdigit()]):
            added = True
        else:
            error = dl.get_error()

    query = (request.params.get("regexp") or "").strip()
    show_all = os.environ.get("SHOW_ALL_CONTACTS", "0") in ("1", "true", "True")
    options = []
    if query or show_all:
        book = AFAddressBook(db=request.dbsession)
        numbers = book.numbers_by_company()
        for company in (book.search_companies(query) if query else book.get_companies()):
            for number in numbers.get(company.get("abook_id"), []):
                options.append({"value": f"{number['abookfax_id']}|{number['faxnumber']}",
                                "label": f"{company.get('company')} - {number['faxnumber']}"})
    return {"title": "- NamiFAX - Distribution List Helper", "dl_id": dl_id, "query": query, "options": options,
            "added": added, "error": error}


@view_config(route_name="popup_distro_contacts", permission="view")
def popup_distro_contacts(request):
    """Distro contacts selector popup matching distrocontacts.php."""
    dl = DistributionList(db=request.dbsession)
    options_html = []

    try:
        groups = dl.get_distrolists()
        if groups:
            for g in groups:
                gid = g.get("dl_id", 1)
                gname = g.get("listname", "")
                options_html.append(f'          <option value="{gid}">{html.escape(gname)}</option>')
    except Exception:
        pass

    select_content = "\n".join(options_html)

    html_content = f"""<!DOCTYPE html>
<html>
<head><title>- NamiFAX - Distribution Contacts</title></head>
<body class="bg-slate-50 text-slate-800 p-4">
  <div class="max-w-md mx-auto bg-white p-4 rounded shadow border border-slate-200">
    <h2 class="text-base font-bold text-sky-900 mb-3">Distribution Contacts</h2>
    <form name="myform" class="space-y-3">
      <div>
        <label for="regexp" class="block text-xs font-semibold mb-1">Search:</label>
        <input type="text" name="regexp" id="regexp" class="w-full border border-slate-300 rounded px-2 py-1 text-sm" />
      </div>
      <div>
        <select name="dl_id" id="dl_id" size="6" class="w-full border border-slate-300 rounded p-1 text-sm">
{select_content}
        </select>
      </div>
      <div class="pt-2 flex justify-end space-x-2">
        <input type="button" name="add" value="Add" class="px-3 py-1 bg-sky-800 text-white rounded text-sm cursor-pointer hover:bg-sky-700" />
        <input type="button" value="Close Window" onclick="window.close()" class="px-3 py-1 bg-slate-200 text-slate-700 rounded text-sm cursor-pointer hover:bg-slate-300" />
      </div>
    </form>
  </div>
</body>
</html>"""
    return Response(html_content, content_type="text/html")


@view_config(route_name="popup_fax_contacts", permission="view")
def popup_fax_contacts(request):
    """Fax contacts selector popup matching faxcontacts.php."""
    ab = AFAddressBook(db=request.dbsession)
    options_html = []

    try:
        companies = ab.get_companies()
        if companies:
            for c in companies:
                cid = c.get("ab_id") or c.get("abook_id") or 1
                cname = c.get("company", "")
                faxnum = c.get("faxnum") or c.get("faxnumber") or ""
                label = f"{cname} - {faxnum}" if faxnum else cname
                options_html.append(f'          <option value="{cid}">{html.escape(label)}</option>')
    except Exception:
        pass

    select_content = "\n".join(options_html)

    html_content = f"""<!DOCTYPE html>
<html>
<head><title>- NamiFAX - Fax Contacts</title></head>
<body class="bg-slate-50 text-slate-800 p-4">
  <div class="max-w-md mx-auto bg-white p-4 rounded shadow border border-slate-200">
    <h2 class="text-base font-bold text-sky-900 mb-3">Fax Contacts</h2>
    <form name="myform" class="space-y-3">
      <div>
        <label for="regexp" class="block text-xs font-semibold mb-1">Search:</label>
        <input type="text" name="regexp" id="regexp" class="w-full border border-slate-300 rounded px-2 py-1 text-sm" />
      </div>
      <div>
        <select name="myselect" id="myselect" size="6" class="w-full border border-slate-300 rounded p-1 text-sm">
{select_content}
        </select>
      </div>
      <div class="pt-2 flex justify-end space-x-2">
        <input type="button" name="add" value="Add" class="px-3 py-1 bg-sky-800 text-white rounded text-sm cursor-pointer hover:bg-sky-700" />
        <input type="button" value="Close Window" onclick="window.close()" class="px-3 py-1 bg-slate-200 text-slate-700 rounded text-sm cursor-pointer hover:bg-slate-300" />
      </div>
    </form>
  </div>
</body>
</html>"""
    return Response(html_content, content_type="text/html")


@view_config(route_name="popup_email_contacts", permission="view")
def popup_email_contacts(request):
    """Email contacts selector popup matching emailcontacts.php."""
    ab = AFAddressBook(db=request.dbsession)
    options_html = []

    try:
        contacts = ab.get_contacts()
        if contacts:
            for eid, cstr in contacts.items():
                options_html.append(f'          <option value="{eid}">{html.escape(cstr)}</option>')
    except Exception:
        pass

    select_content = "\n".join(options_html)

    html_content = f"""<!DOCTYPE html>
<html>
<head><title>- NamiFAX - Email Contacts</title></head>
<body class="bg-slate-50 text-slate-800 p-4">
  <div class="max-w-md mx-auto bg-white p-4 rounded shadow border border-slate-200">
    <h2 class="text-base font-bold text-sky-900 mb-3">Email Contacts</h2>
    <form name="myform" class="space-y-3">
      <div>
        <label for="regexp" class="block text-xs font-semibold mb-1">Search:</label>
        <input type="text" name="regexp" id="regexp" class="w-full border border-slate-300 rounded px-2 py-1 text-sm" />
      </div>
      <div>
        <select name="abookemail_id" id="abookemail_id" size="6" class="w-full border border-slate-300 rounded p-1 text-sm">
{select_content}
        </select>
      </div>
      <div class="pt-2 flex justify-end space-x-2">
        <input type="button" name="add" value="Add" class="px-3 py-1 bg-sky-800 text-white rounded text-sm cursor-pointer hover:bg-sky-700" />
        <input type="button" value="Close Window" onclick="window.close()" class="px-3 py-1 bg-slate-200 text-slate-700 rounded text-sm cursor-pointer hover:bg-slate-300" />
      </div>
    </form>
  </div>
</body>
</html>"""
    return Response(html_content, content_type="text/html")


def _vcard_lines(request) -> tuple[list[str] | None, str | None]:
    """The lines of the uploaded vCard file, or ``(None, error)``; ``(None, None)`` when no file was sent."""
    upload = request.POST.get("upload")
    if upload is None or not hasattr(upload, "file"):
        return None, None
    content = upload.file.read()
    text = content.decode("utf-8", errors="replace") if isinstance(content, bytes) else str(content)
    if not text.strip():
        return None, None
    if "BEGIN:VCARD" not in text.upper():
        return None, "vCard file problem: this does not look like a vCard (.vcf) file"
    return [line.strip() for line in text.splitlines()], None


def _vcard_value(line: str) -> str:
    return line.split(":", 1)[1].strip()


def _is_card_start(line: str) -> bool:
    return line.upper().startswith("BEGIN:VCARD")


def _upload_page(title: str, intro: str, action: str, message: str | None, error: str | None, extra_field: str = "") -> Response:
    notice = ""
    if error:
        notice = f'<div class="mb-4 p-3 bg-rose-50 border border-rose-200 text-rose-700 rounded text-sm">{html.escape(error)}</div>'
    elif message:
        notice = f'<div class="mb-4 p-3 bg-emerald-50 border border-emerald-200 text-emerald-700 rounded text-sm">{html.escape(message)}</div>'
    page = f"""<!DOCTYPE html>
<html>
<head><title>- NamiFAX - {html.escape(title)}</title></head>
<body class="bg-slate-50 text-slate-800 p-6">
  <div class="max-w-md mx-auto bg-white p-6 rounded shadow border border-slate-200">
    <h1 class="text-xl font-bold mb-4 text-sky-900">Upload Contacts</h1>
    {notice}
    <p class="text-sm text-slate-600 mb-4">{html.escape(intro)}</p>
    <form action="{action}" method="post" enctype="multipart/form-data" class="space-y-4">
{extra_field}      <div>
        <label class="block text-sm font-semibold mb-1">vCard file:</label>
        <input type="file" name="upload" class="w-full border border-slate-300 rounded p-1 text-sm" />
      </div>
      <input type="hidden" name="_submit_check" value="1" />
      <div class="pt-2 flex justify-end">
        <button type="submit" class="px-4 py-2 bg-sky-800 text-white rounded text-sm font-medium hover:bg-sky-700">Upload</button>
      </div>
    </form>
  </div>
</body>
</html>"""
    return Response(page, content_type="text/html")


@view_config(route_name="upload_contacts", permission="view")
def upload_email_contacts(request):
    """Upload a vCard to import e-mail contacts (the original upload_contacts.php).

    Every address line of a card that has a name is added to the e-mail book; the page says how many were new.
    """
    message = error = None
    if request.method == "POST":
        lines, error = _vcard_lines(request)
        count = 0
        if lines:
            book = AFAddressBook(db=request.dbsession)
            name = None
            for line in lines:
                if _is_card_start(line):
                    name = None                                  # a card without a name must not reuse the previous one's
                elif "FN:" in line:
                    name = _vcard_value(line)
                elif "EMAIL" in line and ":" in line and ("EMAIL;" in line or line.upper().startswith("EMAIL:")):
                    email = _vcard_value(line)
                    if name and email and book.create_contact(name, email):
                        count += 1
        if not error:
            message = f"Successfully uploaded {count} contacts"
    return _upload_page("Upload Email Contacts", "Select a vCard (.vcf) file to import email contacts.",
                        "/upload/contacts", message, error)


@view_config(route_name="upload_faxcontacts", permission="view")
def upload_fax_contacts(request):
    """Upload a vCard to import fax contacts (the original upload_faxcontacts.php).

    Each FAX line makes a company (the card's organisation, else its person) with that number, the person and the chosen
    category. E-mail lines go to the e-mail book and are not counted. Like the original, once an organisation has been
    used for a company it is not used again, so a following number or card falls back to its person's name.
    """
    message = error = None
    if request.method == "POST":
        catid = request.POST.get("catid")
        catid_int = int(catid) if catid and str(catid).isdigit() else None
        lines, error = _vcard_lines(request)
        count = 0
        if lines:
            book = AFAddressBook(db=request.dbsession)
            name = org = None
            for line in lines:
                if _is_card_start(line):
                    name = org = None
                elif "FN:" in line:
                    name = _vcard_value(line)
                elif line.upper().startswith("ORG:"):
                    org = _vcard_value(line).replace(";", "").strip()
                elif "EMAIL;" in line or line.upper().startswith("EMAIL:"):
                    email = _vcard_value(line)
                    if name and email:
                        book.create_contact(name, email)
                elif "FAX:" in line or ("TEL" in line.upper() and "FAX" in line.upper() and ":" in line):
                    number = _vcard_value(line).replace(";", "").strip()
                    org = org or name
                    if org and number and book.create(org):
                        org = None
                        count += 1
                        if book.create_faxnumid(number):
                            book.save_settings({"description": None, "faxcatid": catid_int, "to_person": name,
                                                "to_location": None, "to_voicenumber": None})
        if not error:
            message = f"Successfully uploaded {count} contacts"

    category_options = []
    try:
        for cat in FaxPDFCategory(db=request.dbsession).get_categories() or []:
            category_options.append(f'          <option value="{cat.get("catid")}">{html.escape(str(cat.get("name", "")))}</option>')
    except Exception:
        pass
    field = ('''      <div>
        <label class="block text-sm font-semibold mb-1">Category:</label>
        <select name="catid" class="w-full border border-slate-300 rounded px-2 py-1.5 text-sm">
''' + "\n".join(category_options) + '''
        </select>
      </div>
''')
    return _upload_page("Upload Fax Contacts", "Select a vCard (.vcf) file to import fax contacts into address book.",
                        "/upload/faxcontacts", message, error, field)
