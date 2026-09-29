#!/usr/bin/env python3
"""AvantFAX modern CLI replacement for includes/phb.php.

Generates HylaFAX client phonebook file (PBOOK1.1 format) from the AvantFAX AddressBook.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Sequence

# Ensure src directory is on sys.path
SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from namifax.services.addressbook import AFAddressBook

DEFAULT_PHONEBOOK_PATH = os.environ.get("PHONEBOOK", "/var/spool/hylafax/etc/phonebook")


def generate_phonebook_content(addressbook: AFAddressBook) -> str:
    """Generate HylaFAX PBOOK1.1 stream content from address book."""
    out = ["PBOOK1.1"]

    companies = addressbook.get_companies()
    if companies:
        for entry in companies:
            cname = entry.get("company", "")
            cid = entry.get("abook_id")
            out.append(f"{cname}|")

            addressbook.loadbycid(cid)
            faxnums = addressbook.get_faxnums()
            valid_nums = [f.get("faxnumber") for f in faxnums if f.get("faxnumber")]
            out.append(";".join(valid_nums))
            out.append("|||||||")

    return "".join(out)


def run_phb(argv: Sequence[str] | None = None, addressbook: AFAddressBook | None = None) -> int:
    """Execute phonebook export logic."""
    parser = argparse.ArgumentParser(description="Generate HylaFAX phonebook from AvantFAX address book.")
    parser.add_argument(
        "-o",
        "--output",
        default=DEFAULT_PHONEBOOK_PATH,
        help=f"Target phonebook path (default: {DEFAULT_PHONEBOOK_PATH})",
    )
    args = parser.parse_args(argv[1:] if argv is not None else None)

    if addressbook is None:
        addressbook = AFAddressBook()

    content = generate_phonebook_content(addressbook)

    out_path = os.path.abspath(args.output)
    parent_dir = os.path.dirname(out_path)
    if parent_dir and not os.path.exists(parent_dir):
        try:
            os.makedirs(parent_dir, exist_ok=True)
        except OSError:
            pass

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)

    return 0


def export_phonebook(output_path: str = DEFAULT_PHONEBOOK_PATH, addressbook: AFAddressBook | None = None) -> int:
    """Convenience helper to export phonebook directly."""
    return run_phb(["phb", "-o", output_path], addressbook=addressbook)


def main() -> None:
    sys.exit(run_phb(sys.argv))


if __name__ == "__main__":
    main()

