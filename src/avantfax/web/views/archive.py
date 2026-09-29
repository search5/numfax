"""AvantFAX Web Archive view handler."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from avantfax.common.helpers import get_company_details
from avantfax.services.archive_base import FaxPDFArchive


class ArchiveHandler:
    """Handles permanent archive searching, filtering, and deletion."""

    def search_archive(
        self,
        user: Any,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 0,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """Search faxes in archive based on filters and user rights."""
        archive = FaxPDFArchive()
        f = filters or {}

        # Set user permissions
        is_super = getattr(user, "superuser", False)
        devices = [] if is_super else (user.get_modemdevs() if hasattr(user, "get_modemdevs") else [])
        faxcats = None if is_super else (user.get_faxcats() if hasattr(user, "get_faxcats") else None)
        archive.viewable_devices(devices, faxcats)

        criteria = {
            "keywords": f.get("kw") or f.get("keywords"),
            "category": f.get("category_id") or f.get("category"),
            "companyid": f.get("company_id") or f.get("companyid"),
            "start_date": f.get("start_date"),
            "end_date": f.get("end_date"),
            "sentrecvd": f.get("sentrecvd"),
            "userid": None if is_super else getattr(user, "uid", None),
            "superuser": is_super,
            "pageindex": page,
            "pagelimit": limit,
        }

        # Compatible with both search() mock and search_archive() real implementation
        if hasattr(archive, "get_results_count"):
            if hasattr(archive, "search"):
                archive.search(
                    query=criteria["keywords"],
                    sentrecvd=criteria["sentrecvd"],
                    companyid=criteria["companyid"],
                    category=criteria["category"],
                    start_date=criteria["start_date"],
                    end_date=criteria["end_date"],
                    userid=criteria["userid"],
                )
            total_count = archive.get_results_count()
        elif hasattr(archive, "search_archive"):
            total_count = archive.search_archive(criteria)
        else:
            total_count = 0

        try:
            total_count_int = int(total_count)
            num_pages = math.ceil(total_count_int / limit) if total_count_int > limit else 1
        except (TypeError, ValueError):
            num_pages = 1

        items: List[Dict[str, Any]] = []
        if hasattr(archive, "search_results"):
            while archive.search_results(page, limit):
                comp_info = get_company_details(
                    archive.get_faxnumid(),
                    archive.get_origfaxnum(),
                    archive.get_companyid(),
                )
                items.append({
                    "fid": archive.get_fid(),
                    "pages": archive.get_pages(),
                    "tiffpath": archive.get_tiffpath(),
                    "thumbnail": archive.get_thumbnail(),
                    "archstamp": str(archive.get_archstamp() or ""),
                    "inbox": archive.get_inbox(),
                    "company": comp_info.get("company"),
                    "faxnumber": comp_info.get("faxnumber"),
                })
        else:
            while True:
                fid = archive.next_archive_entry()
                if not fid:
                    break
                if archive.load_fax(fid):
                    comp_info = get_company_details(
                        archive.get_faxnumid(),
                        archive.get_origfaxnum(),
                        archive.get_companyid(),
                    )
                    items.append({
                        "fid": archive.get_fid(),
                        "pages": archive.get_pages(),
                        "tiffpath": archive.get_tiffpath(),
                        "thumbnail": archive.get_thumbnail(),
                        "archstamp": str(archive.get_archstamp() or ""),
                        "inbox": archive.get_inbox(),
                        "company": comp_info.get("company"),
                        "faxnumber": comp_info.get("faxnumber"),
                    })

        return {
            "items": items,
            "total_count": total_count,
            "num_pages": num_pages,
            "current_page": page,
            "limit": limit,
        }

    def get_archive_fax(self, fid: int, user: Any) -> Optional[Dict[str, Any]]:
        """Fetch details of a single archived fax."""
        archive = FaxPDFArchive()
        if not archive.load_fax(fid):
            return None

        if not getattr(user, "superuser", False):
            if not archive.user_has_rights(
                getattr(user, "uid", 0),
                user.get_modemdevs(),
                user.get_didrouting(),
                user.get_faxcats(),
            ):
                return None

        comp_info = get_company_details(
            archive.get_faxnumid(),
            archive.get_origfaxnum(),
            archive.get_companyid(),
        )

        return {
            "fid": archive.get_fid(),
            "pages": archive.get_pages(),
            "tiffpath": archive.get_tiffpath(),
            "images": archive.get_faximages(),
            "archstamp": str(archive.get_archstamp() or ""),
            "inbox": archive.get_inbox(),
            "company": comp_info.get("company"),
            "faxnumber": comp_info.get("faxnumber"),
        }

    def delete_archive_fax(self, fid: int, user: Any) -> bool:
        """Permanently delete fax from archive."""
        archive = FaxPDFArchive()
        if not archive.load_fax(fid):
            return False

        if not getattr(user, "superuser", False):
            if not archive.user_has_rights(
                getattr(user, "uid", 0),
                user.get_modemdevs(),
                user.get_didrouting(),
                user.get_faxcats(),
            ):
                return False

        return bool(archive.del_fax(fid))
