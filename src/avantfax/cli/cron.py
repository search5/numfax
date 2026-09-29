#!/usr/bin/env python3
"""AvantFAX modern CLI replacement for includes/avantfaxcron.php.

Handles daily maintenance tasks including temporary directory cleanup and fax retention pruning.
"""

from __future__ import annotations

import getopt
import os
import shutil
import sys
import time
from typing import Sequence

# Ensure src directory is on sys.path
SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from avantfax.services.archive_base import FaxPDFArchive
from avantfax.services.archive_in import ArchiveIn

USAGE = """usage: avantfaxcron.php [-i num-days] [-d num-days] -t num-days
options:
 -i num-days\tprune Inbox of faxes older than number of days
 -d num-days\tdelete faxes from Inbox/Archive that are older than number of days
 -t num-days\tclean AvantFAX temporary directory of files older than number of days
"""

DEFAULT_TMPDIR = os.environ.get("AVANTFAX_TMPDIR", "/tmp/avantfax/")


def deltree(path: str) -> None:
    """Recursively delete directory tree or single file."""
    if os.path.isdir(path):
        shutil.rmtree(path, ignore_errors=True)
    elif os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


def run_cron(
    argv: Sequence[str] | None = None,
    archive_in: ArchiveIn | None = None,
    archive_base: FaxPDFArchive | None = None,
    tmp_dir: str | None = None,
) -> int:
    """Execute cron tasks based on command line options."""
    args = list(argv[1:]) if argv is not None else list(sys.argv[1:])

    try:
        opts, _ = getopt.getopt(args, "i:t:d:")
    except getopt.GetoptError:
        print(USAGE, end="")
        return 0

    opt_dict = dict(opts)

    # -t option is mandatory
    if "-t" not in opt_dict:
        print(USAGE, end="")
        return 0

    try:
        tmpdays = int(opt_dict["-t"])
    except ValueError:
        print(USAGE, end="")
        return 0

    recdays = int(opt_dict["-i"]) if "-i" in opt_dict else None
    deldays = int(opt_dict["-d"]) if "-d" in opt_dict else None

    # 1. Prune old faxes from Inbox
    if recdays is not None:
        inbox_svc = archive_in or ArchiveIn()
        inbox_svc.prune_inbox(recdays)

    # 2. Delete faxes from Inbox/Archive
    if deldays is not None:
        arch_svc = archive_base or FaxPDFArchive()
        arch_svc.prune_archive(deldays)

    # 3. Clean temporary directory
    target_tmp = tmp_dir or DEFAULT_TMPDIR
    if os.path.exists(target_tmp):
        now = time.time()
        for item in os.listdir(target_tmp):
            if item in (".", "..", "index.html"):
                continue

            full_p = os.path.join(target_tmp, item)
            try:
                mtime = os.path.getmtime(full_p)
                diff_days = round((now - mtime) / 86400)
                if diff_days >= tmpdays:
                    deltree(full_p)
            except OSError:
                pass

    return 0


def main() -> None:
    sys.exit(run_cron(sys.argv))


if __name__ == "__main__":
    main()
