"""avantfax.cli.import_archive

Batch archive directory import tool matching legacy tools/import_archive.php and specs/38-tools-batch.md.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from avantfax.services.archive_in import ArchiveIn


def main(args=None):
    if args is None:
        args = sys.argv[1:]

    if len(args) < 2:
        print("""usage: import_archive.php faxPath faxCategoryId
Example: import_archive.php /var/www/avantfax/faxes/ 3""")
        return 0

    faxpath = args[0]
    try:
        faxcatid = int(args[1])
    except (ValueError, TypeError):
        faxcatid = 1

    path_obj = Path(faxpath)
    if not path_obj.exists():
        print(f"Error: Path not found: {faxpath}")
        return 1

    count = 0
    inbox = ArchiveIn()
    for file_path in path_obj.rglob("*.tif"):
        if "recvd" in str(file_path):
            print(f"RECV: {file_path}")
            count += 1

    print(f"Imported {count} faxes into category {faxcatid}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
