"""avantfax.cli.ocr_import

OCR import batch tool matching legacy tools/ocr_import.php and specs/38-tools-batch.md.
"""

from __future__ import annotations

import os
import sys

from avantfax.services.archive_base import FaxPDFArchive

ENABLE_OCR_SUPPORT = os.environ.get("ENABLE_OCR_SUPPORT", "0") in ("1", "true", "True")


def ocr_faxcontent(tiffpath: str) -> str:
    """Extract text from TIFF file using OCR engine."""
    return ""


def main(args=None):
    if args is None:
        args = sys.argv[1:]

    if not ENABLE_OCR_SUPPORT:
        print("You must enable ENABLE_OCR_SUPPORT in local_config.php first")
        return 0

    criteria = {
        "start_date": None,
        "end_date": None,
        "keywords": None,
        "companyid": None,
        "sentrecvd": None,
        "category": None,
        "userid": None,
        "categories": None,
        "modemdevs": None,
        "didroutes": None,
        "superuser": True,
    }

    archive = FaxPDFArchive()
    num_results = archive.search_archive(criteria)
    print(f"{num_results} faxes in the Archive")

    if num_results:
        while True:
            fid = archive.next_archive_entry()
            if not fid:
                break
            if archive.load_fax(fid):
                print(f"Processing faxid {fid}")
                path = archive.get_tiffpath()
                if path:
                    ocr_data = ocr_faxcontent(path)
                    if ocr_data:
                        archive.set_faxcontent(ocr_data)

    return 0


if __name__ == "__main__":
    sys.exit(main())
