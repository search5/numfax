#!/usr/bin/env python3
"""AvantFAX modern CLI replacement for includes/faxcover.php.

Generates HylaFAX fax cover pages by parsing command line options, resolving
user account details, and substituting placeholders into EPS/PS/HTML templates.
"""

from __future__ import annotations

import datetime
import getopt
import os
import re
import sys
import textwrap
from typing import Any, Dict, List, Sequence

# Ensure src directory is on sys.path
SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from namifax.common.helpers import (
    avantfaxlog,
    invalid_email,
    rem_nl,
)
from namifax.db.provider import cli_db

USAGE = (
    "Usage: faxcover [-t to] [-c comments] [-p #pages] [-l to-location] [-m maxcomments] [-z maxlencomments] "
    "[-r regarding] [-v to-voice-number] [-x to-company] [-C template-file] [-D date-format] [-L from-location] "
    "[-M from-mail-address] [-N from-fax-number] [-V from-voice-number] [-X from-company] [-s pagesize] "
    "-f from -n fax-number\n"
)

INSTALLDIR = os.environ.get("AVANTFAX_INSTALLDIR", "/var/www/avantfax")
COVERPAGE_FILE = os.environ.get("COVERPAGE_FILE", "cover.ps")
COVERPAGE_MATCH = os.environ.get("COVERPAGE_MATCH", "XXXX-")
CPAGE_LINELEN = int(os.environ.get("CPAGE_LINELEN", "80"))
FAXCOVER_DATE_FORMAT = os.environ.get("FAXCOVER_DATE_FORMAT", "%Y-%m-%d %H:%M:%S")
FROM_COMPANY = os.environ.get("FROM_COMPANY", "")
FROM_LOCATION = os.environ.get("FROM_LOCATION", "")
FROM_VOICENUMBER = os.environ.get("FROM_VOICENUMBER", "")
FROM_FAXNUMBER = os.environ.get("FROM_FAXNUMBER", "")


def process_template(template_path: str, match: str, values: Dict[str, Any]) -> List[str]:
    """Substitute XXXX-key tokens in template file."""
    if not os.path.exists(template_path):
        return []

    lines: List[str] = []
    with open(template_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            for k, v in values.items():
                token = f"{match}{k}"
                if token in line:
                    line = line.replace(token, str(v) if v is not None else "")
            lines.append(line)
    return lines


def _first_row(db: Any, sql: str) -> Dict[str, Any] | None:
    """Run a SELECT and return the first record, or None."""
    if db.query(sql).executed:
        records = db.get_records()
        if records:
            return records[0]
    return None


def _resolve_sender(db: Any, from_name: str, from_email: str | None) -> tuple[str, str | None]:
    """Resolve sender display name / email from UserAccount (legacy faxcover.php lookup)."""
    if from_email:
        row = _first_row(db, f"SELECT name FROM UserAccount WHERE email = {db.quote(from_email)}")
        if row:
            return row.get("name", from_name), from_email
        if not invalid_email(from_name):
            row2 = _first_row(db, f"SELECT name FROM UserAccount WHERE email = {db.quote(from_name)}")
            if row2:
                return row2.get("name", from_name), from_name
        return from_name, from_email

    row = _first_row(db, f"SELECT email FROM UserAccount WHERE name = {db.quote(from_name)}")
    if row:
        return from_name, row.get("email", from_email)
    row_u = _first_row(db, f"SELECT name, email FROM UserAccount WHERE username = {db.quote(from_name)}")
    if row_u:
        return row_u.get("name", from_name), row_u.get("email", from_email)
    return from_name, from_email


def run_faxcover(argv: Sequence[str] | None = None, *, db: Any = None) -> int:
    """Execute faxcover page generator."""
    args = list(argv[1:]) if argv is not None else list(sys.argv[1:])

    try:
        opts, _ = getopt.getopt(args, "t:c:p:l:m:z:r:v:x:C:D:L:N:V:X:s:f:n:M:")
    except getopt.GetoptError:
        print(USAGE, end="")
        return 0

    opt_dict: Dict[str, str] = dict(opts)

    if "-f" not in opt_dict or "-n" not in opt_dict:
        print(USAGE, end="")
        return 0

    from_name = opt_dict["-f"]
    from_email = opt_dict.get("-M")
    to_fax = opt_dict["-n"]

    avantfaxlog(f"faxcover> from: '{from_name}' email: '{from_email}'", echo=False)

    # Optional DB lookup for user details
    try:
        if db is not None:
            from_name, from_email = _resolve_sender(db, from_name, from_email)
        else:
            with cli_db() as opened:
                from_name, from_email = _resolve_sender(opened, from_name, from_email)
    except Exception:
        pass

    # Template selection
    coverpage_file = os.path.join(INSTALLDIR, "images", COVERPAGE_FILE)
    if "-C" in opt_dict:
        custom_c = opt_dict["-C"]
        coverpage_file = custom_c if os.path.exists(custom_c) else os.path.join(INSTALLDIR, "images", custom_c)

    date_fmt = opt_dict.get("-D", FAXCOVER_DATE_FORMAT)
    try:
        today_date = datetime.datetime.now().strftime(date_fmt)
    except Exception:
        today_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    values: Dict[str, Any] = {
        "from": from_name,
        "from-mail-address": from_email,
        "to": opt_dict.get("-t"),
        "to-company": opt_dict.get("-x"),
        "to-location": opt_dict.get("-l"),
        "to-voice-number": opt_dict.get("-v"),
        "to-fax-number": to_fax,
        "regarding": opt_dict.get("-r"),
        "from-company": opt_dict.get("-X", FROM_COMPANY),
        "from-location": opt_dict.get("-L", FROM_LOCATION),
        "from-voice-number": opt_dict.get("-V", FROM_VOICENUMBER),
        "from-fax-number": opt_dict.get("-N", FROM_FAXNUMBER),
        "page-count": opt_dict.get("-p"),
        "pageSize": opt_dict.get("-s"),
        "todays-date": today_date,
    }

    # Comments parsing
    fax_comments = opt_dict.get("-c", "")
    # Parse {key:val} syntax
    custom_tags = re.findall(r"{([^}]*)}", fax_comments)
    for tag in custom_tags:
        parts = tag.split(":", 1)
        if len(parts) == 2:
            values[parts[0].strip()] = parts[1].strip().strip("'")
    fax_comments = re.sub(r"{([^}]*)}", "", fax_comments)

    maxlen = int(opt_dict.get("-z", CPAGE_LINELEN))
    if fax_comments:
        wrapped_lines = textwrap.wrap(fax_comments, width=maxlen)
        for idx, line in enumerate(wrapped_lines):
            values[f"comments{idx}"] = rem_nl(line)

    if os.path.exists(coverpage_file):
        tpl = process_template(coverpage_file, COVERPAGE_MATCH, values)
        sys.stdout.write("".join(tpl))

    return 0


def main() -> None:
    code = run_faxcover()
    sys.exit(code)


if __name__ == "__main__":
    main()
