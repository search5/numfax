"""AvantFAX Web Inbox view handler."""

from __future__ import annotations

import math
import os
from typing import Any, Dict, List, Optional

from avantfax.common.helpers import get_company_details
from avantfax.services.archive_in import ArchiveIn
from avantfax.services.did import DIDRouting
from avantfax.services.modem import FaxModem


class InboxHandler:
    """Handles inbox viewing, pagination, and fax details."""

    def __init__(self, enable_did_routing: bool = False) -> None:
        self.enable_did_routing = enable_did_routing

    def _get_user_devices_and_cats(self, user: Any) -> tuple[List[str], Optional[List[int]]]:
        """Resolve devices and categories visible to the user."""
        modem_svc = FaxModem()
        did_svc = DIDRouting()

        if getattr(user, "superuser", False):
            devices = did_svc.get_routes() if self.enable_did_routing else modem_svc.get_modems()
            faxcats = None
        else:
            devices = user.get_didrouting() if self.enable_did_routing else user.get_modemdevs()
            faxcats = user.get_faxcats()

        return devices or [], faxcats

    def list_inbox(
        self,
        user: Any,
        page: int = 0,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """Fetch inbox faxes with pagination for given user."""
        inbox = ArchiveIn()
        modem_svc = FaxModem()
        devices, faxcats = self._get_user_devices_and_cats(user)

        total_count = inbox.get_num_faxes(devices, faxcats)
        num_pages = math.ceil(total_count / limit) if total_count > limit else 1
        page = max(0, min(page, num_pages - 1)) if num_pages > 0 else 0

        items: List[Dict[str, Any]] = []
        while inbox.list_inbox(devices, page, limit, faxcats):
            dev = inbox.get_modemdev()
            alias = dev
            if dev and modem_svc.load_device(dev):
                alias = modem_svc.get_alias() or dev

            comp_info = get_company_details(
                inbox.get_faxnumid(),
                inbox.get_origfaxnum(),
                inbox.get_companyid(),
            )

            items.append({
                "fid": inbox.get_fid(),
                "pages": inbox.get_pages(),
                "tiffpath": inbox.get_tiffpath(),
                "thumbnail": inbox.get_thumbnail(),
                "archstamp": str(inbox.get_archstamp() or ""),
                "modemdev": dev,
                "modem_alias": alias,
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

    def get_fax_detail(self, fid: int, user: Any) -> Optional[Dict[str, Any]]:
        """Fetch detailed information and images for a single inbox fax."""
        inbox = ArchiveIn()
        devices, faxcats = self._get_user_devices_and_cats(user)
        inbox.viewable_devices(devices, faxcats)

        if not inbox.load_fax(fid):
            return None

        if not inbox.get_inbox():
            return None

        if not getattr(user, "superuser", False):
            if not inbox.user_has_rights(
                getattr(user, "uid", 0),
                user.get_modemdevs(),
                user.get_didrouting(),
                user.get_faxcats(),
            ):
                return None

        comp_info = get_company_details(
            inbox.get_faxnumid(),
            inbox.get_origfaxnum(),
            inbox.get_companyid(),
        )

        return {
            "fid": inbox.get_fid(),
            "pages": inbox.get_pages(),
            "tiffpath": inbox.get_tiffpath(),
            "images": inbox.get_faximages(),
            "prev_fid": inbox.get_fid_prev(),
            "next_fid": inbox.get_fid_next(),
            "archstamp": str(inbox.get_archstamp() or ""),
            "company": comp_info.get("company"),
            "faxnumber": comp_info.get("faxnumber"),
        }

    def delete_fax(self, fid: int, user: Any) -> bool:
        """Delete an inbox fax."""
        inbox = ArchiveIn()
        if not inbox.load_fax(fid) or not inbox.get_inbox():
            return False
        return inbox.archivefax(fid)

    def archive_fax(self, fid: int, user: Any) -> bool:
        """Move inbox fax to standard archive."""
        inbox = ArchiveIn()
        if not inbox.load_fax(fid) or not inbox.get_inbox():
            return False
        return inbox.archivefax(fid)
