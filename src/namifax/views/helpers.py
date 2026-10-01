"""NamiFAX popup helper dialogs and vCard upload views matching legacy NamiFAX."""

import html
from pyramid.response import Response
from pyramid.view import view_config

from namifax.services.addressbook import AFAddressBook
from namifax.services.categories import FaxPDFCategory
from namifax.services.distro import DistributionList


@view_config(route_name="popup_distrolist_helper")
def popup_distrolist_helper(request):
    """Distribution list contact multi-select helper popup matching distrolist_helper.php."""
    dl_id = request.params.get("dl_id", "1")
    ab = AFAddressBook(db=request.db)
    dl = DistributionList(db=request.db)

    if request.method == "POST":
        myselect = request.params.getall("myselect[]") or request.params.getall("myselect")
        if myselect and dl_id.isdigit():
            try:
                if dl.load_list(int(dl_id)):
                    dl.add_entries(myselect)
            except Exception:
                pass

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
<head><title>- NamiFAX - Distribution List Helper</title></head>
<body class="bg-slate-50 text-slate-800 p-4">
  <div class="max-w-md mx-auto bg-white p-4 rounded shadow border border-slate-200">
    <h2 class="text-base font-bold text-sky-900 mb-3">Distribution List Helper</h2>
    <form action="/helper/distrolist" method="post" class="space-y-3">
      <div>
        <label for="regexp" class="block text-xs font-semibold mb-1">Search:</label>
        <input type="text" name="regexp" id="regexp" class="w-full border border-slate-300 rounded px-2 py-1 text-sm" />
      </div>
      <div>
        <select name="myselect[]" id="myselect" multiple="multiple" size="6" class="w-full border border-slate-300 rounded p-1 text-sm">
{select_content}
        </select>
      </div>
      <input type="hidden" name="dl_id" value="{html.escape(str(dl_id))}" />
      <input type="hidden" name="_submit_check" value="1" />
      <div class="pt-2 flex justify-end space-x-2">
        <input type="submit" name="add" value="Add" class="px-3 py-1 bg-sky-800 text-white rounded text-sm cursor-pointer hover:bg-sky-700" />
        <input type="button" value="Close Window" onclick="window.close()" class="px-3 py-1 bg-slate-200 text-slate-700 rounded text-sm cursor-pointer hover:bg-slate-300" />
      </div>
    </form>
  </div>
</body>
</html>"""
    return Response(html_content, content_type="text/html")


@view_config(route_name="popup_distro_contacts")
def popup_distro_contacts(request):
    """Distro contacts selector popup matching distrocontacts.php."""
    dl = DistributionList(db=request.db)
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


@view_config(route_name="popup_fax_contacts")
def popup_fax_contacts(request):
    """Fax contacts selector popup matching faxcontacts.php."""
    ab = AFAddressBook(db=request.db)
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


@view_config(route_name="popup_email_contacts")
def popup_email_contacts(request):
    """Email contacts selector popup matching emailcontacts.php."""
    ab = AFAddressBook(db=request.db)
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


@view_config(route_name="upload_contacts")
def upload_email_contacts(request):
    """Upload vCard to import email contacts matching upload_contacts.php."""
    numcontacts = 0
    if request.method == "POST":
        upload_file = request.POST.get("upload")
        if upload_file is not None and hasattr(upload_file, "file"):
            content = upload_file.file.read()
            lines = content.decode("utf-8", errors="ignore").splitlines() if isinstance(content, bytes) else str(content).splitlines()

            ab = AFAddressBook(db=request.db)
            current_name = None
            for line in lines:
                line = line.strip()
                if line.startswith("FN:"):
                    current_name = line.split(":", 1)[1].strip()
                elif "EMAIL" in line and ":" in line:
                    email = line.split(":", 1)[1].strip()
                    if current_name and email:
                        if ab.create_contact(current_name, email):
                            numcontacts += 1

    html = f"""<!DOCTYPE html>
<html>
<head><title>- NamiFAX - Upload Email Contacts</title></head>
<body class="bg-slate-50 text-slate-800 p-6">
  <div class="max-w-md mx-auto bg-white p-6 rounded shadow border border-slate-200">
    <h1 class="text-xl font-bold mb-4 text-sky-900">Upload Contacts</h1>
    <p class="text-sm text-slate-600 mb-4">Select a vCard (.vcf) file to import email contacts.</p>
    <form action="/upload/contacts" method="post" enctype="multipart/form-data" class="space-y-4">
      <div>
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
    return Response(html, content_type="text/html")


@view_config(route_name="upload_faxcontacts")
def upload_fax_contacts(request):
    """Upload vCard to import fax contacts matching upload_faxcontacts.php."""
    numcontacts = 0
    if request.method == "POST":
        upload_file = request.POST.get("upload")
        catid = request.POST.get("catid")
        try:
            catid_int = int(catid) if catid else None
        except (ValueError, TypeError):
            catid_int = None

        if upload_file is not None and hasattr(upload_file, "file"):
            content = upload_file.file.read()
            lines = content.decode("utf-8", errors="ignore").splitlines() if isinstance(content, bytes) else str(content).splitlines()

            ab = AFAddressBook(db=request.db)
            current_name = None
            current_org = None
            current_work = None
            for line in lines:
                line = line.strip()
                if line.startswith("FN:"):
                    current_name = line.split(":", 1)[1].strip()
                elif line.startswith("ORG:"):
                    current_org = line.split(":", 1)[1].replace(";", "").strip()
                elif "FAX:" in line or ("TEL" in line and "FAX" in line and ":" in line):
                    fax_num = line.split(":", 1)[1].replace(";", "").strip()
                    org_name = current_org or current_name or "Unknown"
                    if ab.create(org_name):
                        numcontacts += 1
                        if ab.create_faxnumid(fax_num):
                            ab.save_settings({
                                "description": None,
                                "faxcatid": catid_int,
                                "to_person": current_name,
                                "to_location": None,
                                "to_voicenumber": current_work,
                            })
                elif "EMAIL" in line and ":" in line:
                    email = line.split(":", 1)[1].strip()
                    if current_name and email:
                        ab.create_contact(current_name, email)

    category_options = []
    try:
        cats = FaxPDFCategory(db=request.db).get_categories() or []
        for cat in cats:
            cid = cat.get("catid")
            cname = html.escape(str(cat.get("name", "")))
            category_options.append(f'          <option value="{cid}">{cname}</option>')
    except Exception:
        pass

    cat_content = "\n".join(category_options)

    html_content = f"""<!DOCTYPE html>
<html>
<head><title>- NamiFAX - Upload Fax Contacts</title></head>
<body class="bg-slate-50 text-slate-800 p-6">
  <div class="max-w-md mx-auto bg-white p-6 rounded shadow border border-slate-200">
    <h1 class="text-xl font-bold mb-4 text-sky-900">Upload Contacts</h1>
    <p class="text-sm text-slate-600 mb-4">Select a vCard (.vcf) file to import fax contacts into address book.</p>
    <form action="/upload/faxcontacts" method="post" enctype="multipart/form-data" class="space-y-4">
      <div>
        <label class="block text-sm font-semibold mb-1">Category:</label>
        <select name="catid" class="w-full border border-slate-300 rounded px-2 py-1.5 text-sm">
{cat_content}
        </select>
      </div>
      <div>
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
    return Response(html_content, content_type="text/html")
