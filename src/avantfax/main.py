#!/usr/bin/env python3
"""AvantFAX modern entry point.

Unified CLI for system services, HylaFAX hooks, cron maintenance, and web server.
"""

from __future__ import annotations

import os
import sys
from wsgiref.simple_server import make_server

# Ensure src directory is on sys.path
SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from avantfax.cli.cron import run_cron
from avantfax.cli.dynconf import run_dynconf
from avantfax.cli.faxcover import run_faxcover
from avantfax.cli.faxrcvd import run_faxrcvd
from avantfax.cli.notify import run_notify
from avantfax.cli.phb import main as run_phb
from avantfax.web.app import create_app

USAGE = """AvantFAX Modernized System CLI

Usage:
  avantfax <command> [arguments]

Available commands:
  serve       Start the HTTP / API web service (default: 0.0.0.0:8000)
  dynconf     Execute HylaFAX dynamic configuration call filter
  cron        Execute periodic maintenance and archive cleanup
  notify      Execute HylaFAX outbound post-send notification hook
  faxrcvd     Execute HylaFAX inbound received fax processing hook
  faxcover    Generate HylaFAX fax cover page
  phb         Generate HylaFAX PBOOK1.1 format phonebook

Run 'avantfax <command> --help' for details on a specific command.
"""


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]

    if not args:
        print(USAGE)
        return 0

    cmd = args[0]
    sub_args = args[1:]

    if cmd in ("-h", "--help", "help"):
        print(USAGE)
        return 0

    if cmd == "serve":
        host = os.environ.get("AVANTFAX_HOST", "0.0.0.0")
        port = int(os.environ.get("AVANTFAX_PORT", "8000"))
        app = create_app()
        print(f"[*] Starting AvantFAX Web Service on http://{host}:{port} ...")
        with make_server(host, port, app) as httpd:
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\n[*] Server stopped.")
        return 0

    elif cmd == "dynconf":
        return run_dynconf(["dynconf"] + sub_args)

    elif cmd == "cron":
        return run_cron(["avantfaxcron.php"] + sub_args)

    elif cmd == "notify":
        return run_notify(["notify.php"] + sub_args)

    elif cmd == "faxrcvd":
        return run_faxrcvd(["faxrcvd.php"] + sub_args)

    elif cmd == "faxcover":
        return run_faxcover(["faxcover.php"] + sub_args)

    elif cmd == "phb":
        return run_phb()

    else:
        print(f"Unknown command: {cmd}\n")
        print(USAGE)
        return 1


if __name__ == "__main__":
    sys.exit(main())
