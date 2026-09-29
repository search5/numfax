"""AvantFAX Web Outbox view handler."""

from __future__ import annotations

from typing import Any, Dict, List

from avantfax.services.addressbook import AFAddressBook
from avantfax.services.faxqueue import FaxQueue


class OutboxHandler:
    """Handles outbox queues, status monitoring, and job cancellation."""

    def _resolve_companies(self, queue: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Augment queue items with company name from address book."""
        ab = AFAddressBook()
        result: List[Dict[str, Any]] = []

        for item in queue:
            entry = dict(item)
            num = entry.get("number", "")
            entry["company"] = num
            if num and ab.loadbyfaxnum(num):
                entry["company"] = ab.get_company() or num
            result.append(entry)

        return result

    def get_outbox_queue(self, user: Any) -> Dict[str, Any]:
        """Fetch active and failed queues for given user."""
        fq = FaxQueue()
        is_superuser = getattr(user, "superuser", False)
        username = getattr(user, "username", "")

        fq.process_queue()
        active_raw = fq.get_queue() if is_superuser else fq.list_owner(username)

        fq.process_failed_queue()
        failed_raw = fq.get_queue() if is_superuser else fq.list_owner(username)

        return {
            "active_queue": self._resolve_companies(active_raw or []),
            "failed_queue": self._resolve_companies(failed_raw or []),
        }

    def kill_job(self, jid: str, user: Any) -> bool:
        """Cancel queue job if owned by user or if superuser."""
        fq = FaxQueue()
        is_superuser = getattr(user, "superuser", False)
        username = getattr(user, "username", "")

        active = fq.get_queue() if is_superuser else fq.list_owner(username)
        target = None
        for q in (active or []):
            if str(q.get("jid")) == str(jid):
                target = q
                break

        if not target:
            fq.process_failed_queue()
            failed = fq.get_queue() if is_superuser else fq.list_owner(username)
            for q in (failed or []):
                if str(q.get("jid")) == str(jid):
                    target = q
                    break

        if not target:
            return False

        owner = target.get("owner", username)
        return bool(fq.killjob(owner, str(jid)))
