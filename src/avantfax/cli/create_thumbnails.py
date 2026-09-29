"""avantfax.cli.create_thumbnails

Batch thumbnail generation matching legacy tools/create_thumbnails.php and specs/38-tools-batch.md.
"""

from __future__ import annotations

import os
import sys

from avantfax.common.helpers import pdf_preview
from avantfax.services.archive_base import FaxPDFArchive, PREVIMG, PREVIMGSFX


def main(args=None):
    if args is None:
        args = sys.argv[1:]

    criteria = {
        "start_date": None,
        "end_date": None,
        "keywords": None,
        "companyid": None,
        "sentrecvd": "*",
        "category": None,
        "faxid": None,
        "userid": None,
        "categories": None,
        "modemdevs": None,
        "didroutes": None,
        "superuser": True,
    }

    archive = FaxPDFArchive()
    results = archive.search_archive(criteria)

    if results:
        print(f"{results} faxes in Archive")
        fax = FaxPDFArchive()
        while True:
            fid = archive.next_archive_entry()
            if not fid:
                break

            fax.load_fax(fid)
            thumbnail = fax.get_thumbnail() or ""
            path = os.path.dirname(thumbnail)
            preview = os.path.join(path, f"{PREVIMG}0{PREVIMGSFX}")

            if os.path.isfile(thumbnail) and os.path.isfile(preview):
                continue

            print(f"Creating images in: {path}")
            pdf_preview(path)
    else:
        print("No faxes found")

    print("Done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
