#!/usr/bin/env python3
"""Generate Web E2E Golden Master Datasets for NamiFAX / AvantFAX.

Creates contract.json and response.html for 20 core web scenarios
derived from legacy AvantFAX PHP + Smarty markup and form specifications.
"""

import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]          # the project root (dev/golden_master/<file>)
WEB_GOLDEN_DIR = ROOT_DIR / "dev" / "golden_master" / "web"

SCENARIOS = [
    {
        "id": "W01_login_get",
        "description": "Login page initial GET request",
        "route": "/",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "title": "- AvantFAX - Login",
            "forms": [
                {
                    "method": "post",
                    "action": "/login",
                    "inputs": [
                        {"name": "username", "type": "text", "required": True},
                        {"name": "password", "type": "password", "required": True},
                        {"name": "_submit_check", "type": "hidden", "value": "1"},
                    ],
                    "submit_button": True
                }
            ],
            "required_links": ["/forgot", "http://www.avantfax.com"],
            "required_text": [":: AvantFAX LOGIN ::", "AvantFAX", "3.3.5"]
        },
        "html_content": """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" dir="ltr">
<head>
<title>- AvantFAX - Login</title>
<meta http-equiv="Content-Type" content="text/html; UTF-8" />
<link rel="icon" href="/static/favicon.ico" type="image/x-icon" />
<link rel="stylesheet" href="/static/css/main.css" type="text/css" />
</head>
<body class="bg-slate-100 text-slate-800">
<div id="main" class="max-w-4xl mx-auto my-12 bg-white rounded-lg shadow-md border border-slate-300 p-8">
  <div id="header" class="flex justify-between items-center border-b pb-4 mb-8">
    <div class="text-xl font-bold text-sky-800 tracking-wide">:: AvantFAX LOGIN ::</div>
    <div class="text-right">
      <a href="http://www.avantfax.com" target="_blank"><img src="/static/images/avantfax-big.png" border="0" alt="AvantFAX" class="h-10 inline" /></a>
      <p class="text-xs text-slate-500 mt-1 font-semibold">3.3.5</p>
    </div>
  </div>
  <div id="content" class="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
    <div class="border-r border-slate-200 pr-8">
      <p class="font-semibold text-sky-900 mb-2">Welcome to AvantFAX Web Portal</p>
      <p class="text-sm text-slate-600 mb-6">Enter your username and password to access incoming and outgoing faxes.</p>
      <p><a href="/forgot" class="text-amber-800 underline text-sm hover:text-amber-900">Forgot your password?</a></p>
    </div>
    <div class="pl-4">
      <form action="/login" method="post" class="space-y-4">
        <div>
          <label for="username" class="block text-xs font-bold text-slate-700 uppercase mb-1">Username</label>
          <input type="text" name="username" id="username" class="w-full border border-slate-300 rounded px-3 py-2 text-sm focus:ring-1 focus:ring-sky-600 focus:outline-none" autofocus="autofocus" />
        </div>
        <div>
          <label for="password" class="block text-xs font-bold text-slate-700 uppercase mb-1">Password</label>
          <input type="password" name="password" id="password" class="w-full border border-slate-300 rounded px-3 py-2 text-sm focus:ring-1 focus:ring-sky-600 focus:outline-none" />
        </div>
        <input type="hidden" name="_submit_check" value="1" />
        <button type="submit" class="px-4 py-2 bg-sky-800 text-white rounded text-sm font-semibold hover:bg-sky-700 transition">Login</button>
      </form>
    </div>
  </div>
</div>
</body>
</html>"""
    },
    {
        "id": "W02_login_fail",
        "description": "Login failure with invalid credentials",
        "route": "/login",
        "method": "POST",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "title": "- AvantFAX - Login",
            "forms": [{"method": "post", "action": "/login"}],
            "required_text": ["Invalid username or password", ":: AvantFAX LOGIN ::"]
        },
        "html_content": """<!DOCTYPE html>
<html>
<head><title>- AvantFAX - Login</title></head>
<body>
<div class="error text-red-600 bg-red-50 p-2 border border-red-200 rounded">Invalid username or password</div>
<form action="/login" method="post">
  <input type="text" name="username" value="baduser" />
  <input type="password" name="password" />
  <input type="hidden" name="_submit_check" value="1" />
  <button type="submit">Login</button>
</form>
</body>
</html>"""
    },
    {
        "id": "W03_login_success",
        "description": "Login success with redirect to inbox",
        "route": "/login",
        "method": "POST",
        "expected_status": 302,
        "contract": {
            "status_code": 302,
            "redirect_location": "/inbox",
            "set_cookie": True
        },
        "html_content": ""
    },
    {
        "id": "W04_inbox_empty",
        "description": "Empty inbox page for authenticated user",
        "route": "/inbox?empty=1",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "title": "- AvantFAX - Inbox",
            "required_links": ["/inbox", "/sendfax", "/archive", "/outbox", "/addressbook", "/settings", "/logout"],
            "required_text": ["0 FAXES", "Inbox", "MODEM", "IDLE"]
        },
        "html_content": """<!DOCTYPE html>
<html>
<head><title>- AvantFAX - Inbox</title></head>
<body>
<div id="nav-top">
  <a href="/inbox">Inbox</a>
  <a href="/sendfax">Send Fax</a>
  <a href="/archive">Archive</a>
  <a href="/outbox">Outbox</a>
  <a href="/addressbook">Contacts</a>
  <a href="/settings">Settings</a>
  <a href="/logout">Logout</a>
</div>
<div id="modem-status-div">ttyS0 [IDLE]</div>
<div id="content">
  <p>0 FAXES</p>
</div>
</body>
</html>"""
    },
    {
        "id": "W05_inbox_list",
        "description": "Inbox with list of received faxes and 9 action buttons",
        "route": "/inbox",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "title": "- AvantFAX - Inbox",
            "table_headers": ["FROM", "DATE", "MODEM/DID", "PAGES", "ACTIONS"],
            "required_actions": ["viewfax", "rotate", "download", "reply", "email", "note", "archive", "delete"],
            "required_text": ["Acme Corp", "2026-09-29"]
        },
        "html_content": """<!DOCTYPE html>
<html>
<head><title>- AvantFAX - Inbox</title></head>
<body>
<div id="inbox-table">
  <div class="inbox_row" id="faxid_1">
    <span class="from">Acme Corp</span>
    <span class="date">2026-09-29 10:00:00</span>
    <span class="pages">2 pages</span>
    <div class="actions">
      <a href="/viewfax?fid=1" title="View Fax">View</a>
      <a href="/faxes/rotate/1" title="Rotate Fax">Rotate</a>
      <a href="/faxes/download/1" title="Download PDF">PDF</a>
      <a href="/sendfax?refax=1" title="Reply to Fax">Reply</a>
      <a href="/email?fid=1" title="Email Fax">Email</a>
      <a href="/note?fid=1" title="Note">Note</a>
      <a href="/archive/move/1" title="Archive">Archive</a>
      <a href="/delete/1" title="Delete">Delete</a>
    </div>
  </div>
</div>
</body>
</html>"""
    },
    {
        "id": "W06_viewfax_modal",
        "description": "Fax preview and viewer modal dialog",
        "route": "/viewfax?fid=1",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "title": "AvantFAX - View Fax",
            "required_links": ["/faxes/download/1", "/faxes/rotate/1"],
            "required_text": ["FaxID", "Pages"]
        },
        "html_content": """<!DOCTYPE html>
<html>
<head><title>AvantFAX - View Fax</title></head>
<body>
<div id="viewer-container">
  <h2>Fax Viewer - ID 1</h2>
  <a href="/faxes/download/1">Download PDF</a>
  <a href="/faxes/rotate/1">Rotate 90°</a>
  <p>Page 1 of 2</p>
</div>
</body>
</html>"""
    },
    {
        "id": "W07_pdf_download",
        "description": "Streaming PDF binary download endpoint",
        "route": "/faxes/download/1",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "content_type": "application/pdf",
            "binary_stream": True
        },
        "html_content": "%PDF-1.4 Mock Binary PDF Content"
    },
    {
        "id": "W08_outbox_queue",
        "description": "Outbox monitoring queue table",
        "route": "/outbox",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "title": "- AvantFAX - Outbox",
            "table_headers": ["Job ID", "Destination", "Status", "Actions"],
            "required_text": ["Outbox", "No jobs in queue"]
        },
        "html_content": """<!DOCTYPE html>
<html>
<head><title>- AvantFAX - Outbox</title></head>
<body>
<h2>Outbox Jobs Queue</h2>
<p>No jobs in queue</p>
</body>
</html>"""
    },
    {
        "id": "W09_sendfax_form",
        "description": "Fax submission form with file upload",
        "route": "/sendfax",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "title": "- AvantFAX - Send Fax",
            "forms": [
                {
                    "method": "post",
                    "action": "/sendfax",
                    "enctype": "multipart/form-data",
                    "inputs": [
                        {"name": "to_person", "type": "text"},
                        {"name": "to_company", "type": "text"},
                        {"name": "faxnumber", "type": "text", "required": True},
                        {"name": "coverpage", "type": "select"},
                        {"name": "file", "type": "file"},
                        {"name": "_submit_check", "type": "hidden", "value": "1"}
                    ]
                }
            ],
            "required_text": ["Send Fax", "Destination fax numbers"]
        },
        "html_content": """<!DOCTYPE html>
<html>
<head><title>- AvantFAX - Send Fax</title></head>
<body>
<form action="/sendfax" method="post" enctype="multipart/form-data">
  <input type="text" name="to_person" />
  <input type="text" name="to_company" />
  <input type="text" name="faxnumber" required="required" />
  <select name="coverpage"><option value="standard">standard</option></select>
  <input type="file" name="file" />
  <input type="hidden" name="_submit_check" value="1" />
  <button type="submit">Send Fax</button>
</form>
</body>
</html>"""
    },
    {
        "id": "W10_sendfax_err",
        "description": "SendFax validation error when fax number is missing",
        "route": "/sendfax",
        "method": "POST",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "required_text": ["Fax number is required", "Send Fax"]
        },
        "html_content": """<!DOCTYPE html>
<html>
<head><title>- AvantFAX - Send Fax</title></head>
<body>
<div class="error">Fax number is required</div>
<form action="/sendfax" method="post">
  <input type="text" name="faxnumber" value="" />
  <button type="submit">Send Fax</button>
</form>
</body>
</html>"""
    },
    {
        "id": "W11_sendfax_post",
        "description": "Successful fax dispatch redirect to outbox",
        "route": "/sendfax",
        "method": "POST",
        "expected_status": 302,
        "contract": {
            "status_code": 302,
            "redirect_location": "/outbox"
        },
        "html_content": ""
    },
    {
        "id": "W12_archive_form",
        "description": "Archive search and filter view",
        "route": "/archive",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "title": "- AvantFAX - Archive",
            "forms": [
                {
                    "method": "get",
                    "action": "/archive",
                    "inputs": [
                        {"name": "search", "type": "text"},
                        {"name": "category", "type": "select"},
                        {"name": "date_from", "type": "text"},
                        {"name": "date_to", "type": "text"}
                    ]
                }
            ],
            "required_text": ["Archive Search", "Categories"]
        },
        "html_content": """<!DOCTYPE html>
<html>
<head><title>- AvantFAX - Archive</title></head>
<body>
<form action="/archive" method="get">
  <input type="text" name="search" />
  <select name="category"><option value="">All Categories</option></select>
  <input type="text" name="date_from" />
  <input type="text" name="date_to" />
  <button type="submit">Search</button>
</form>
</body>
</html>"""
    },
    {
        "id": "W13_archive_res",
        "description": "Archive search results table with pagination",
        "route": "/archive?kw=test",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "required_text": ["Archive Search", "Results", "test"]
        },
        "html_content": """<!DOCTYPE html>
<html>
<head><title>- AvantFAX - Archive Results</title></head>
<body>
<h2>Archive Search Results</h2>
<p>Results for test</p>
<div class="pagination"><span>1</span></div>
</body>
</html>"""
    },
    {
        "id": "W14_addressbook",
        "description": "Address book companies list",
        "route": "/addressbook",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "title": "- AvantFAX - Contacts",
            "required_links": ["/addressbook/edit"],
            "required_text": ["Address Book", "New Company"]
        },
        "html_content": """<!DOCTYPE html>
<html>
<head><title>- AvantFAX - Contacts</title></head>
<body>
<h2>Address Book</h2>
<a href="/addressbook/edit">New Company</a>
</body>
</html>"""
    },
    {
        "id": "W15_abook_edit",
        "description": "Address book edit company form",
        "route": "/addressbook/edit",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "forms": [
                {
                    "method": "post",
                    "action": "/addressbook/edit",
                    "inputs": [
                        {"name": "company", "type": "text", "required": True},
                        {"name": "faxnumber", "type": "text"},
                        {"name": "email", "type": "text"},
                        {"name": "_submit_check", "type": "hidden", "value": "1"}
                    ]
                }
            ],
            "required_text": ["Company Name", "Fax Number", "Email"]
        },
        "html_content": """<!DOCTYPE html>
<html>
<head><title>Edit Company</title></head>
<body>
<form action="/addressbook/edit" method="post">
  <input type="text" name="company" required="required" />
  <input type="text" name="faxnumber" />
  <input type="text" name="email" />
  <input type="hidden" name="_submit_check" value="1" />
  <button type="submit">Save</button>
</form>
</body>
</html>"""
    },
    {
        "id": "W16_distrolist",
        "description": "Distribution lists management",
        "route": "/distrolist",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "title": "- AvantFAX - Distribution Lists",
            "required_links": ["/distrolist/edit"],
            "required_text": ["Distribution Lists", "Create List"]
        },
        "html_content": """<!DOCTYPE html>
<html>
<head><title>- AvantFAX - Distribution Lists</title></head>
<body>
<h2>Distribution Lists</h2>
<a href="/distrolist/edit">Create List</a>
</body>
</html>"""
    },
    {
        "id": "W17_settings",
        "description": "User preferences and password settings",
        "route": "/settings",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "title": "- AvantFAX - Settings",
            "forms": [
                {
                    "method": "post",
                    "action": "/settings",
                    "inputs": [
                        {"name": "old_password", "type": "password"},
                        {"name": "new_password", "type": "password"},
                        {"name": "confirm_password", "type": "password"}
                    ]
                }
            ],
            "required_text": ["User Settings", "Change Password"]
        },
        "html_content": """<!DOCTYPE html>
<html>
<head><title>- AvantFAX - Settings</title></head>
<body>
<h2>User Settings</h2>
<form action="/settings" method="post">
  <input type="password" name="old_password" />
  <input type="password" name="new_password" />
  <input type="password" name="confirm_password" />
  <button type="submit">Update Password</button>
</form>
</body>
</html>"""
    },
    {
        "id": "W18_admin_dash",
        "description": "Administrator dashboard and server overview",
        "route": "/admin",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "title": "AvantFAX - Admin Control Panel",
            "required_links": ["/admin/users", "/admin/modems", "/admin/did", "/admin/syslog"],
            "required_text": ["Admin Control Panel", "Dashboard", "Server Status"]
        },
        "html_content": """<!DOCTYPE html>
<html>
<head><title>AvantFAX - Admin Control Panel</title></head>
<body>
<div id="admin-menu">
  <a href="/admin/users">Users</a>
  <a href="/admin/modems">Modems</a>
  <a href="/admin/did">DID Routing</a>
  <a href="/admin/syslog">System Logs</a>
</div>
<h2>Admin Dashboard</h2>
<p>Server Status: Active</p>
</body>
</html>"""
    },
    {
        "id": "W19_admin_users",
        "description": "Admin users management view",
        "route": "/admin/users",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "title": "AvantFAX - Admin - Users",
            "forms": [
                {
                    "method": "post",
                    "action": "/admin/users",
                    "inputs": [
                        {"name": "name", "type": "text", "required": True},
                        {"name": "username", "type": "text", "required": True},
                        {"name": "password", "type": "password"},
                        {"name": "email", "type": "email", "required": True},
                        {"name": "_submit_check", "type": "hidden", "value": "1"}
                    ],
                    "submit_button": True
                }
            ],
            "table_headers": ["Username", "Email", "Superuser", "Admin", "Actions"],
            "required_text": ["User Accounts", "Create New User", "DID Routes", "Fax Lines", "Categories"]
        },
        "html_content": """<!DOCTYPE html>
<html>
<head><title>AvantFAX - Admin - Users</title></head>
<body>
<h2>User Accounts</h2>
<table>
  <tr><th>Username</th><th>Email</th><th>Superuser</th><th>Admin</th><th>Actions</th></tr>
</table>
<div id="user-form">
  <form action="/admin/users" method="post">
    <p><label for="name">Name:</label> <input type="text" name="name" id="name" required /></p>
    <p><label for="username">Username:</label> <input type="text" name="username" id="username" required /></p>
    <p><label for="password">Password:</label> <input type="password" name="password" id="password" /></p>
    <p><label for="email">Email:</label> <input type="email" name="email" id="email" required /></p>
    <fieldset><legend>DID Routes</legend></fieldset>
    <fieldset><legend>Fax Lines</legend></fieldset>
    <fieldset><legend>Categories</legend></fieldset>
    <input type="hidden" name="_submit_check" value="1" />
    <button type="submit">Save User</button>
  </form>
</div>
</body>
</html>"""
    },
    {
        "id": "W20_admin_modems",
        "description": "Admin modem device configuration and settings form",
        "route": "/admin/modems",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "title": "AvantFAX - Admin - Modems",
            "forms": [
                {
                    "method": "post",
                    "action": "/admin/modems",
                    "inputs": [
                        {"name": "device", "type": "text", "required": True},
                        {"name": "alias", "type": "text", "required": True},
                        {"name": "contact", "type": "email"},
                        {"name": "printer", "type": "text"},
                        {"name": "_submit_check", "type": "hidden", "value": "1"}
                    ],
                    "submit_button": True
                }
            ],
            "table_headers": ["Device", "Alias", "Contact", "Status"],
            "required_text": ["Fax Modems", "Configure Modems"]
        },
        "html_content": """<!DOCTYPE html>
<html>
<head><title>AvantFAX - Admin - Modems</title></head>
<body>
<h2>Fax Modems</h2>
<table>
  <tr><th>Device</th><th>Alias</th><th>Contact</th><th>Status</th></tr>
</table>
<div id="configure-form">
  <form action="/admin/modems" method="post">
    <p><label for="device">Device:</label> <input type="text" name="device" id="device" required /></p>
    <p><label for="alias">Alias:</label> <input type="text" name="alias" id="alias" required /></p>
    <p><label for="contact">Contact:</label> <input type="email" name="contact" id="contact" /></p>
    <p><label for="printer">Printer:</label> <input type="text" name="printer" id="printer" /></p>
    <input type="hidden" name="_submit_check" value="1" />
    <button type="submit">Save Modem</button>
  </form>
</div>
</body>
</html>"""
    },
    {
        "id": "W21_admin_routing",
        "description": "Admin DID inbound routing configuration",
        "route": "/admin/routing/did",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "title": "AvantFAX - Admin - Configure DID Routing",
            "forms": [
                {
                    "method": "post",
                    "action": "/admin/routing/did",
                    "inputs": [
                        {"name": "route", "type": "text", "required": True},
                        {"name": "alias", "type": "text", "required": True},
                        {"name": "contact", "type": "text"},
                        {"name": "printer", "type": "text"},
                        {"name": "_submit_check", "type": "hidden", "value": "1"}
                    ],
                    "submit_button": True
                }
            ],
            "required_text": ["Configure DID Routing", "Route Code", "Alias", "Printer"]
        },
        "html_content": """<!DOCTYPE html>
<html>
<head><title>AvantFAX - Admin - Configure DID Routing</title></head>
<body>
<h2>Configure DID Routing</h2>
<div id="main-content">
  <form action="/admin/routing/did" method="post">
    <p><label for="route">Route Code:</label> <input type="text" name="route" id="route" required /></p>
    <p><label for="alias">Alias:</label> <input type="text" name="alias" id="alias" required /></p>
    <p><label for="contact">Contact Email:</label> <input type="text" name="contact" id="contact" /></p>
    <p><label for="printer">Printer:</label> <input type="text" name="printer" id="printer" /></p>
    <input type="hidden" name="_submit_check" value="1" />
    <button type="submit">Save</button>
  </form>
</div>
</body>
</html>"""
    },
    {
        "id": "W22_admin_syslogs",
        "description": "Admin system logs viewer and keyword filter",
        "route": "/admin/system_logs",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "title": "AvantFAX - Admin - System Logs",
            "forms": [
                {
                    "method": "get",
                    "action": "/admin/system_logs",
                    "inputs": [
                        {"name": "kw", "type": "text"},
                        {"name": "_submit_check", "type": "hidden", "value": "1"}
                    ],
                    "submit_button": True
                }
            ],
            "table_headers": ["Date", "Log Text"],
            "required_text": ["System Logs", "Keywords", "Date"]
        },
        "html_content": """<!DOCTYPE html>
<html>
<head><title>AvantFAX - Admin - System Logs</title></head>
<body>
<h2>System Logs</h2>
<div align="center">
  <form action="/admin/system_logs" method="get">
    <input type="text" name="kw" id="kw" />
    <input type="hidden" name="_submit_check" value="1" />
    <button type="submit">Search</button>
  </form>
</div>
<table>
  <tr><th>Date</th><th>Log Text</th></tr>
</table>
</body>
</html>"""
    },
    {
        "id": "W23_auth_forgot",
        "description": "Lost password reset recovery form",
        "route": "/forgot",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "title": "- AvantFAX - Lost Password",
            "forms": [
                {
                    "method": "post",
                    "action": "/forgot",
                    "inputs": [
                        {"name": "username", "type": "text"},
                        {"name": "_submit_check", "type": "hidden", "value": "1"}
                    ],
                    "submit_button": True
                }
            ],
            "required_text": ["Lost Password", "Reset Password"]
        },
        "html_content": """<!DOCTYPE html><html><head><title>- AvantFAX - Lost Password</title></head><body><h1>Lost Password Recovery</h1><form action="/forgot" method="post"><input type="text" name="username" /><input type="hidden" name="_submit_check" value="1" /><button type="submit">Reset Password</button></form></body></html>"""
    },
    {
        "id": "W24_auth_pwdexpired",
        "description": "Password expired force update form",
        "route": "/pwdexpired",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "title": "- AvantFAX - Password Expired",
            "forms": [
                {
                    "method": "post",
                    "action": "/pwdexpired",
                    "inputs": [
                        {"name": "oldpwd", "type": "password"},
                        {"name": "newpwd", "type": "password"},
                        {"name": "conpwd", "type": "password"},
                        {"name": "_submit_check", "type": "hidden", "value": "1"}
                    ],
                    "submit_button": True
                }
            ],
            "required_text": ["Password Expired", "Update Password"]
        },
        "html_content": """<!DOCTYPE html><html><head><title>- AvantFAX - Password Expired</title></head><body><h1>:: AvantFAX :: Password Expired</h1><form action="/pwdexpired" method="post"><input type="password" name="oldpwd" /><input type="password" name="newpwd" /><input type="password" name="conpwd" /><input type="hidden" name="_submit_check" value="1" /><button type="submit">Update Password</button></form></body></html>"""
    },
    {
        "id": "W25_admin_covers",
        "description": "Admin configure cover page templates",
        "route": "/admin/covers",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "title": "AvantFAX - Admin - Configure Cover Pages",
            "forms": [
                {
                    "method": "post",
                    "action": "/admin/covers",
                    "inputs": [
                        {"name": "title", "type": "text"},
                        {"name": "file", "type": "text"},
                        {"name": "_submit_check", "type": "hidden", "value": "1"}
                    ],
                    "submit_button": True
                }
            ],
            "required_text": ["Configure Cover Pages", "Title", "File"]
        },
        "html_content": """<!DOCTYPE html><html><head><title>AvantFAX - Admin - Configure Cover Pages</title></head><body><h2>Configure Cover Pages</h2><form action="/admin/covers" method="post"><input type="text" name="title" /><input type="text" name="file" /><input type="hidden" name="_submit_check" value="1" /><button type="submit">Save</button></form></body></html>"""
    },
    {
        "id": "W26_admin_categories",
        "description": "Admin fax category tag manager",
        "route": "/admin/categories",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "title": "AvantFAX - Admin - Fax Categories",
            "forms": [
                {
                    "method": "post",
                    "action": "/admin/categories",
                    "inputs": [
                        {"name": "name", "type": "text"},
                        {"name": "_submit_check", "type": "hidden", "value": "1"}
                    ],
                    "submit_button": True
                }
            ],
            "required_text": ["Fax Categories", "Category Name"]
        },
        "html_content": """<!DOCTYPE html><html><head><title>AvantFAX - Admin - Fax Categories</title></head><body><h2>Fax Categories</h2><form action="/admin/categories" method="post"><input type="text" name="name" /><input type="hidden" name="_submit_check" value="1" /><button type="submit">Save</button></form></body></html>"""
    },
    {
        "id": "W27_admin_barcodes",
        "description": "Admin barcode routing rules manager",
        "route": "/admin/barcodes",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "title": "AvantFAX - Admin - Configure Barcode Routing",
            "forms": [
                {
                    "method": "post",
                    "action": "/admin/barcodes",
                    "inputs": [
                        {"name": "barcode", "type": "text"},
                        {"name": "alias", "type": "text"},
                        {"name": "contact", "type": "text"},
                        {"name": "printer", "type": "text"},
                        {"name": "_submit_check", "type": "hidden", "value": "1"}
                    ],
                    "submit_button": True
                }
            ],
            "required_text": ["Configure Barcode Routing", "Barcode", "Alias"]
        },
        "html_content": """<!DOCTYPE html><html><head><title>AvantFAX - Admin - Configure Barcode Routing</title></head><body><h2>Configure Barcode Routing</h2><form action="/admin/barcodes" method="post"><input type="text" name="barcode" /><input type="text" name="alias" /><input type="text" name="contact" /><input type="text" name="printer" /><input type="hidden" name="_submit_check" value="1" /><button type="submit">Save</button></form></body></html>"""
    },
    {
        "id": "W28_admin_dynconf",
        "description": "Admin dynamic configuration and blacklist",
        "route": "/admin/dynconf",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "title": "AvantFAX - Admin - Dynamic Configuration",
            "forms": [
                {
                    "method": "post",
                    "action": "/admin/dynconf",
                    "inputs": [
                        {"name": "callid", "type": "text"},
                        {"name": "_submit_check", "type": "hidden", "value": "1"}
                    ],
                    "submit_button": True
                }
            ],
            "required_text": ["Dynamic Configuration", "Caller ID", "Modem Device"]
        },
        "html_content": """<!DOCTYPE html><html><head><title>AvantFAX - Admin - Dynamic Configuration</title></head><body><h2>Dynamic Configuration</h2><form action="/admin/dynconf" method="post"><input type="text" name="callid" /><input type="hidden" name="_submit_check" value="1" /><button type="submit">Save</button></form></body></html>"""
    },
    {
        "id": "W29_admin_fax2email",
        "description": "Admin fax to email forwarding configuration",
        "route": "/admin/fax2email",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "title": "AvantFAX - Admin - Fax to Email",
            "forms": [
                {
                    "method": "post",
                    "action": "/admin/fax2email",
                    "inputs": [
                        {"name": "company", "type": "text"},
                        {"name": "email", "type": "text"},
                        {"name": "printer", "type": "text"},
                        {"name": "_submit_check", "type": "hidden", "value": "1"}
                    ],
                    "submit_button": True
                }
            ],
            "required_text": ["Fax to Email", "Company", "Email"]
        },
        "html_content": """<!DOCTYPE html><html><head><title>AvantFAX - Admin - Fax to Email</title></head><body><h2>Fax to Email</h2><form action="/admin/fax2email" method="post"><input type="text" name="company" /><input type="text" name="email" /><input type="text" name="printer" /><input type="hidden" name="_submit_check" value="1" /><button type="submit">Save</button></form></body></html>"""
    },
    {
        "id": "W30_admin_sysfunc",
        "description": "Admin system functions reboot and shutdown",
        "route": "/admin/system_func",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "title": "AvantFAX - Admin - System Functions",
            "forms": [
                {
                    "method": "post",
                    "action": "/admin/system_func",
                    "inputs": [
                        {"name": "_submit_check", "type": "hidden", "value": "1"}
                    ],
                    "submit_button": True
                }
            ],
            "required_text": ["System Functions", "Reboot", "Shutdown", "Download"]
        },
        "html_content": """<!DOCTYPE html><html><head><title>AvantFAX - Admin - System Functions</title></head><body><h2>System Functions</h2><form action="/admin/system_func" method="post"><input type="hidden" name="_submit_check" value="1" /><button type="submit" name="reboot">Reboot</button><button type="submit" name="shutdown">Shutdown</button><button type="submit" name="download_ar">Download</button></form></body></html>"""
    },
    {
        "id": "W31_modal_email",
        "description": "Modal dialog to send fax via email",
        "route": "/email",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "title": "- AvantFAX - Send Fax via Email",
            "forms": [
                {
                    "method": "post",
                    "action": "/email",
                    "inputs": [
                        {"name": "emails", "type": "textarea"},
                        {"name": "subject", "type": "text"},
                        {"name": "msg", "type": "textarea"},
                        {"name": "_submit_check", "type": "hidden", "value": "1"}
                    ],
                    "submit_button": True
                }
            ],
            "required_text": ["Send Fax via Email", "Recipients", "Subject"]
        },
        "html_content": """<!DOCTYPE html><html><head><title>- AvantFAX - Send Fax via Email</title></head><body><h1>Send Fax via Email</h1><form action="/email" method="post"><textarea name="emails"></textarea><input type="text" name="subject" /><textarea name="msg"></textarea><input type="hidden" name="_submit_check" value="1" /><button type="submit">Send</button></form></body></html>"""
    },
    {
        "id": "W32_modal_assign",
        "description": "Modal dialog to assign company name to fax",
        "route": "/assign",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "title": "- AvantFAX - Assign Company",
            "forms": [
                {
                    "method": "post",
                    "action": "/assign",
                    "inputs": [
                        {"name": "regexp", "type": "text"},
                        {"name": "_submit_check", "type": "hidden", "value": "1"}
                    ],
                    "submit_button": True
                }
            ],
            "required_text": ["Assign Company Name", "Search", "Save"]
        },
        "html_content": """<!DOCTYPE html><html><head><title>- AvantFAX - Assign Company</title></head><body><h1>Assign Company Name</h1><form action="/assign" method="post"><input type="text" name="regexp" /><input type="hidden" name="_submit_check" value="1" /><button type="submit">Save</button></form></body></html>"""
    },
    {
        "id": "W33_modal_note",
        "description": "Modal dialog to add note to fax",
        "route": "/note",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "title": "- AvantFAX - Add Note",
            "forms": [
                {
                    "method": "post",
                    "action": "/note",
                    "inputs": [
                        {"name": "description", "type": "textarea"},
                        {"name": "_submit_check", "type": "hidden", "value": "1"}
                    ],
                    "submit_button": True
                }
            ],
            "required_text": ["Add Note", "Note", "Save"]
        },
        "html_content": """<!DOCTYPE html><html><head><title>- AvantFAX - Add Note</title></head><body><h1>Add Note</h1><form action="/note" method="post"><textarea name="description"></textarea><input type="hidden" name="_submit_check" value="1" /><button type="submit">Save</button></form></body></html>"""
    },
    {
        "id": "W34_modal_delete",
        "description": "Modal dialog to confirm fax deletion",
        "route": "/delete",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "title": "- AvantFAX - Delete Fax",
            "forms": [
                {
                    "method": "post",
                    "action": "/delete",
                    "inputs": [
                        {"name": "fid", "type": "hidden"},
                        {"name": "_submit_check", "type": "hidden", "value": "1"}
                    ],
                    "submit_button": True
                }
            ],
            "required_text": ["Delete Fax", "Are you sure you want to delete this fax?"]
        },
        "html_content": """<!DOCTYPE html><html><head><title>- AvantFAX - Delete Fax</title></head><body><h1>Delete Fax</h1><form action="/delete" method="post"><p>Are you sure you want to delete this fax?</p><input type="hidden" name="fid" value="1" /><input type="hidden" name="_submit_check" value="1" /><button type="submit">Delete</button></form></body></html>"""
    },
    {
        "id": "W35_modal_refax",
        "description": "Modal dialog to resend or reply to fax",
        "route": "/refax",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "title": "- AvantFAX - Reply to Fax",
            "forms": [
                {
                    "method": "post",
                    "action": "/refax",
                    "inputs": [
                        {"name": "destinations", "type": "textarea"},
                        {"name": "regarding", "type": "text"},
                        {"name": "comments", "type": "textarea"},
                        {"name": "_submit_check", "type": "hidden", "value": "1"}
                    ],
                    "submit_button": True
                }
            ],
            "required_text": ["Reply to Fax", "Destination", "Comments"]
        },
        "html_content": """<!DOCTYPE html><html><head><title>- AvantFAX - Reply to Fax</title></head><body><h1>Reply to Fax</h1><form action="/refax" method="post"><textarea name="destinations"></textarea><input type="text" name="regarding" /><textarea name="comments"></textarea><input type="hidden" name="_submit_check" value="1" /><button type="submit">Send</button></form></body></html>"""
    },
    {
        "id": "W36_modal_txreport",
        "description": "Transmission report popup dialog",
        "route": "/txreport",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "title": "- AvantFAX - Transmission Report",
            "required_text": ["Transmission Report", "Company", "Date", "Pages", "Print"]
        },
        "html_content": """<!DOCTYPE html><html><head><title>- AvantFAX - Transmission Report</title></head><body><h1>Transmission Report</h1><p>Company: Acme Corp</p><p>Date: 2026-09-29</p><p>Pages: 2</p><button type="button">Print</button></body></html>"""
    },
    {
        "id": "W37_api_modemstatus",
        "description": "Async AJAX modem status XML poller",
        "route": "/ajax/modemstatus",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "content_type": "text/xml",
            "required_text": ["<response>", "<modem>", "<status>"]
        },
        "html_content": """<response><row><modem>ttyS0</modem><status>Idle</status><class>2.0</class></row></response>"""
    },
    {
        "id": "W38_api_inbox_count",
        "description": "Async AJAX inbox unread fax counter",
        "route": "/ajax/inbox",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "content_type": "text/plain",
            "required_text": ["0"]
        },
        "html_content": """0"""
    },
    {
        "id": "W39_api_addressbook_suggest",
        "description": "Async AJAX address book company auto-suggest XML",
        "route": "/ajax/book",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "content_type": "text/xml",
            "required_text": ["<response>", "<company>", "<faxnum>"]
        },
        "html_content": """<response><row><company>Acme Corp - 1234567</company><cid>1</cid><faxnum>1234567</faxnum><fnid>1</fnid></row></response>"""
    },
    {
        "id": "W40_api_emailbook_suggest",
        "description": "Async AJAX email address auto-suggest XML",
        "route": "/ajax/emailbook",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "content_type": "text/xml",
            "required_text": ["<response>", "<email>"]
        },
        "html_content": """<response><row><id>1</id><email>user@example.com</email></row></response>"""
    },
    {
        "id": "W41_api_addressbook_prefill",
        "description": "Async AJAX contact prefill XML data",
        "route": "/ajax/prefillto",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "content_type": "text/xml",
            "required_text": ["<response>", "<to_company>", "<to_person>", "<to_address>"]
        },
        "html_content": """<response><row><to_company>Acme Corp</to_company><to_person>John Doe</to_person><to_address>123 Street</to_address><to_zip>12345</to_zip><to_city>City</to_city><to_location>HQ</to_location><to_voicenumber>555-1234</to_voicenumber></row></response>"""
    },
    {
        "id": "W42_api_distrolist_faxes",
        "description": "Async AJAX distribution list fax numbers string",
        "route": "/ajax/dlist",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "content_type": "text/plain"
        },
        "html_content": """1234567; 9876543"""
    },
    {
        "id": "W43_api_archive_fax",
        "description": "Async AJAX archive fax endpoint",
        "route": "/ajax/archivefax",
        "method": "POST",
        "expected_status": 200,
        "contract": {
            "status_code": 200
        },
        "html_content": """"""
    },
    {
        "id": "W44_api_faxalter",
        "description": "Modal dialog to modify queued fax job attributes",
        "route": "/ajax/faxalter",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "title": "- AvantFAX - Modify Fax Job",
            "forms": [
                {
                    "method": "post",
                    "action": "/ajax/faxalter",
                    "inputs": [
                        {"name": "destination", "type": "text"},
                        {"name": "priority", "type": "select"},
                        {"name": "numtries", "type": "text"},
                        {"name": "sendtime", "type": "checkbox"},
                        {"name": "killtime", "type": "text"},
                        {"name": "jid", "type": "hidden"},
                        {"name": "_submit_check", "type": "hidden", "value": "1"}
                    ],
                    "submit_button": True
                }
            ],
            "required_text": ["Modify Fax Job", "New Destination", "Priority", "Save"]
        },
        "html_content": """<!DOCTYPE html><html><head><title>- AvantFAX - Modify Fax Job</title></head><body><h1>Modify Fax Job</h1><form id="faxalter" action="/ajax/faxalter" method="post"><p><label for="dest">New Destination:</label><input type="text" name="destination" id="dest" /></p><p><label for="priority">Priority:</label><select name="priority" id="priority"><option value="*"></option></select></p><p><label for="numtries">Number of tries:</label><input type="text" name="numtries" id="numtries" /></p><p><label for="killtime">Kill time:</label><input type="text" name="killtime" id="killtime" /></p><p><input type="checkbox" name="sendtime" id="sendtime" value="1" /></p><input type="hidden" name="jid" value="1" /><input type="hidden" name="_submit_check" value="1" /><button type="submit">Save</button></form></body></html>"""
    },
    {
        "id": "W45_popup_distro_helper",
        "description": "Popup helper dialog to select contacts for distribution list",
        "route": "/helper/distrolist?dl_id=1",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "title": "- AvantFAX - Distribution List Helper",
            "forms": [
                {
                    "method": "post",
                    "action": "/helper/distrolist?dl_id=1",
                    "inputs": [
                        {"name": "regexp", "type": "text"},
                        {"name": "myselect[]", "type": "select"},
                        {"name": "dl_id", "type": "hidden"},
                        {"name": "_submit_check", "type": "hidden", "value": "1"}
                    ],
                    "submit_button": True
                }
            ],
            "required_text": ["Search", "Add", "Close Window"]
        },
        "html_content": """<!DOCTYPE html><html><head><title>- AvantFAX - Distribution List Helper</title></head><body><form action="/helper/distrolist?dl_id=1" method="post"><p><label for="regexp">Search:</label><input type="text" name="regexp" id="regexp" /></p><select name="myselect[]" id="myselect" multiple="multiple"></select><input type="hidden" name="dl_id" value="1" /><input type="hidden" name="_submit_check" value="1" /><input type="submit" name="add" value="Add" /><input type="button" value="Close Window" /></form></body></html>"""
    },
    {
        "id": "W46_popup_distro_contacts",
        "description": "Popup dialog to select distribution group for fax recipient",
        "route": "/helper/distrocontacts",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "title": "- AvantFAX - Distribution Contacts",
            "forms": [
                {
                    "inputs": [
                        {"name": "regexp", "type": "text"},
                        {"name": "dl_id", "type": "select"}
                    ]
                }
            ],
            "required_text": ["Search", "Add", "Close Window"]
        },
        "html_content": """<!DOCTYPE html><html><head><title>- AvantFAX - Distribution Contacts</title></head><body><form name="myform"><p><label for="regexp">Search:</label><input type="text" name="regexp" id="regexp" /></p><select name="dl_id" id="dl_id"></select><input type="button" name="add" value="Add" /><input type="button" value="Close Window" /></form></body></html>"""
    },
    {
        "id": "W47_popup_fax_contacts",
        "description": "Popup dialog to select address book contacts for fax recipient",
        "route": "/helper/faxcontacts",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "title": "- AvantFAX - Fax Contacts",
            "forms": [
                {
                    "inputs": [
                        {"name": "regexp", "type": "text"},
                        {"name": "myselect", "type": "select"}
                    ]
                }
            ],
            "required_text": ["Search", "Add", "Close Window"]
        },
        "html_content": """<!DOCTYPE html><html><head><title>- AvantFAX - Fax Contacts</title></head><body><form name="myform"><p><label for="regexp">Search:</label><input type="text" name="regexp" id="regexp" /></p><select name="myselect" id="myselect"></select><input type="button" name="add" value="Add" /><input type="button" value="Close Window" /></form></body></html>"""
    },
    {
        "id": "W48_popup_email_contacts",
        "description": "Popup dialog to select email contacts from address book",
        "route": "/helper/emailcontacts",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "title": "- AvantFAX - Email Contacts",
            "forms": [
                {
                    "inputs": [
                        {"name": "regexp", "type": "text"},
                        {"name": "abookemail_id", "type": "select"}
                    ]
                }
            ],
            "required_text": ["Search", "Add", "Close Window"]
        },
        "html_content": """<!DOCTYPE html><html><head><title>- AvantFAX - Email Contacts</title></head><body><form name="myform"><p><label for="regexp">Search:</label><input type="text" name="regexp" id="regexp" /></p><select name="abookemail_id" id="abookemail_id"></select><input type="button" name="add" value="Add" /><input type="button" value="Close Window" /></form></body></html>"""
    },
    {
        "id": "W49_upload_contacts",
        "description": "Upload vCard file to import email contacts",
        "route": "/upload/contacts",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "title": "- AvantFAX - Upload Email Contacts",
            "forms": [
                {
                    "method": "post",
                    "action": "/upload/contacts",
                    "inputs": [
                        {"name": "upload", "type": "file"},
                        {"name": "_submit_check", "type": "hidden", "value": "1"}
                    ],
                    "submit_button": True
                }
            ],
            "required_text": ["Upload Contacts", "vCard"]
        },
        "html_content": """<!DOCTYPE html><html><head><title>- AvantFAX - Upload Email Contacts</title></head><body><h1>Upload Contacts</h1><form action="/upload/contacts" method="post" enctype="multipart/form-data"><p>Select vCard file:</p><input type="file" name="upload" /><input type="hidden" name="_submit_check" value="1" /><button type="submit">Upload</button></form></body></html>"""
    },
    {
        "id": "W50_upload_faxcontacts",
        "description": "Upload vCard file to import fax contacts",
        "route": "/upload/faxcontacts",
        "method": "GET",
        "expected_status": 200,
        "contract": {
            "status_code": 200,
            "title": "- AvantFAX - Upload Fax Contacts",
            "forms": [
                {
                    "method": "post",
                    "action": "/upload/faxcontacts",
                    "inputs": [
                        {"name": "upload", "type": "file"},
                        {"name": "catid", "type": "select"},
                        {"name": "_submit_check", "type": "hidden", "value": "1"}
                    ],
                    "submit_button": True
                }
            ],
            "required_text": ["Upload Contacts", "Category", "vCard"]
        },
        "html_content": """<!DOCTYPE html><html><head><title>- AvantFAX - Upload Fax Contacts</title></head><body><h1>Upload Contacts</h1><form action="/upload/faxcontacts" method="post" enctype="multipart/form-data"><p>Select Category:</p><select name="catid"><option value="1">General</option></select><p>Select vCard file:</p><input type="file" name="upload" /><input type="hidden" name="_submit_check" value="1" /><button type="submit">Upload</button></form></body></html>"""
    }
]

def main():
    WEB_GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[*] Generating {len(SCENARIOS)} Web E2E Golden Master Datasets into {WEB_GOLDEN_DIR}...")
    
    for s in SCENARIOS:
        s_id = s["id"]
        s_dir = WEB_GOLDEN_DIR / s_id
        s_dir.mkdir(parents=True, exist_ok=True)
        
        meta = {
            "id": s["id"],
            "description": s["description"],
            "route": s["route"],
            "method": s["method"],
            "expected_status": s["expected_status"],
            "implemented": s.get("implemented", True if int(s["id"][1:3]) <= 50 else False)
        }
        (s_dir / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        (s_dir / "contract.json").write_text(json.dumps(s["contract"], indent=2, ensure_ascii=False), encoding="utf-8")
        (s_dir / "response.html").write_text(s["html_content"], encoding="utf-8")
        print(f"  [+] Created Golden Master for {s_id}")

    print(f"[✓] Successfully generated all {len(SCENARIOS)} Web Golden Master datasets!")

if __name__ == "__main__":
    main()
