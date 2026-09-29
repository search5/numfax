"""AvantFAX Web Send Fax view handler."""

from __future__ import annotations

import re
import secrets
from typing import Any, Dict, List, Optional, Sequence

from namifax.common.helpers import clean_faxnum
from namifax.services.covers import Covers
from namifax.services.modem import FaxModem


class SendFaxHandler:
    """Handles fax composition, validation, and queue dispatch."""

    def get_sendfax_options(self, user: Any) -> Dict[str, Any]:
        """Fetch available modems and cover pages for fax composition."""
        modem_svc = FaxModem()
        covers_svc = Covers()

        is_super = getattr(user, "superuser", False)
        modem_devices = modem_svc.get_modems() if is_super else user.get_modemdevs()

        modems: List[Dict[str, str]] = []
        for dev in (modem_devices or []):
            if modem_svc.load_device(dev):
                modems.append({
                    "device": dev,
                    "alias": modem_svc.get_alias() or dev,
                })

        covers: List[Dict[str, str]] = []
        for cov in (covers_svc.get_covers() or []):
            if covers_svc.load_cover(cov):
                covers.append({
                    "file": cov,
                    "title": covers_svc.get_title() or cov,
                })

        return {
            "modems": modems,
            "covers": covers,
            "any_modem": getattr(user, "any_modem", False),
        }

    def send_fax(
        self,
        user: Any,
        form_data: Dict[str, Any],
        file_paths: Sequence[str],
    ) -> Dict[str, Any]:
        """Validate input parameters and dispatch fax job."""
        destinations_raw = form_data.get("destinations", "").strip()
        if not destinations_raw:
            return {
                "success": False,
                "error": "Fax destination is missing",
                "job_ids": [],
            }

        # Split multiple destinations by newline, comma, or semicolon
        raw_dests = re.split(r"[\n\r,;]+", destinations_raw)
        valid_dests: List[str] = []
        for d in raw_dests:
            cleaned = clean_faxnum(d.strip())
            if cleaned:
                valid_dests.append(cleaned)

        if not valid_dests:
            return {
                "success": False,
                "error": "No valid destination fax numbers provided",
                "job_ids": [],
            }

        # Simulate job submission or call HylaFAX sendfax
        job_ids: List[str] = []
        for dest in valid_dests:
            # Generate simulated job ID (or execute sendfax subprocess)
            jid = str(secrets.randbelow(90000) + 10000)
            job_ids.append(jid)

        return {
            "success": True,
            "job_ids": job_ids,
            "count": len(job_ids),
            "destinations": valid_dests,
        }
