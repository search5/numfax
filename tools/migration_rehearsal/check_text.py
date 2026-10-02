"""Do names that the legacy application stored come out as text? The legacy application stores accented letters as HTML entities
(``M&uuml;ller``) and relied on the browser to draw them. Prints, for each screen, how many entities are shown as letters of text.
Exit status 1 with --strict when any is."""
import os
import re
import sys

import webtest

from namifax import create_app

app = create_app(**{"sqlalchemy.url": os.environ["REH_URL"]})
client = webtest.TestApp(app, extra_environ={"HTTP_HOST": "example.com"})
client.post("/login", {"username": "carol", "password": "Carol#2013xy", "_submit_check": "1"})

shown = 0
for label, path in (("address book", "/addressbook"), ("e-mail book", "/emailbook"), ("users", "/admin/users"),
                    ("modems", "/admin/modems"), ("categories", "/admin/categories")):
    text = re.sub(r"<[^>]+>", " ", client.get(path, expect_errors=True).text)
    found = re.findall(r"&amp;[A-Za-z]+;|&amp;#\d+;", text)
    shown += len(found)
    print(f"{label:13} {'entities shown as text: ' + ', '.join(sorted(set(found))[:4]) if found else 'clean'}")
print("RESULT:", "entities are shown as text" if shown else "clean")
sys.exit(1 if shown and "--strict" in sys.argv else 0)
