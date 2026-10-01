"""Which faxes a signed-in user may see, change and delete (the original's ``user_has_rights`` rules).

A superuser works with every fax. Anybody else works with the faxes of the modems (or DID routes) and fax categories on
their account and with the faxes they sent themselves; deleting also needs the account's ``can_del`` flag.
The rights are read from the database on each request, so a change made by an administrator applies at once.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, List, Optional

from namifax.services.user_account import AFUserAccount


def _did_routing_enabled() -> bool:
    return os.environ.get("ENABLE_DID_ROUTING", "0") in ("1", "true", "True")


@dataclass(frozen=True)
class FaxAccess:
    uid: Optional[int] = None
    username: str = ""
    superuser: bool = False
    can_del: bool = False
    modems: List[str] = field(default_factory=list)
    routes: List[str] = field(default_factory=list)
    faxcats: List[str] = field(default_factory=list)

    @classmethod
    def for_request(cls, request: Any) -> "FaxAccess":
        """The rights of the user behind ``request``; nobody (no rights at all) when the account cannot be found."""
        identity = request.identity or {}
        username = str(identity.get("username") or "")
        account = AFUserAccount(db=request.dbsession)
        if not username or not account.load_username(username):
            return cls(username=username)
        data = account.dbdata
        return cls(
            uid=account.get_uid(),
            username=username,
            superuser=bool(data.get("superuser")),
            can_del=bool(data.get("can_del")),
            modems=account.get_modemdevs(),
            routes=account.get_didrouting(),
            faxcats=account.get_faxcats(),
        )

    # --- what to pass to the listing and counting functions -------------------------------------------------------------

    @property
    def did_routing(self) -> bool:
        return _did_routing_enabled()

    @property
    def devices(self) -> Optional[List[str]]:
        """Modems (or DID routes) the inbox is limited to; ``None`` for no limit."""
        if self.superuser:
            return None
        return self.routes if self.did_routing else self.modems

    @property
    def categories(self) -> Optional[List[str]]:
        return None if self.superuser else self.faxcats

    def search_rights(self) -> dict:
        """The viewing rights part of the archive search criteria."""
        return {"superuser": self.superuser, "modemdevs": self.modems, "didroutes": self.routes,
                "categories": self.faxcats, "enable_did_routing": self.did_routing}

    # --- single faxes -----------------------------------------------------------------------------------------------------------

    def may_use(self, fax: Any) -> bool:
        """May this user see and change the loaded fax (``fax`` is an ArchiveIn/FaxPDFArchive with a fax loaded)?"""
        if self.superuser:
            return True
        return fax.user_has_rights(self.uid or 0, self.modems, self.routes, self.faxcats)

    def may_delete(self, fax: Any) -> bool:
        return self.superuser or (self.can_del and self.may_use(fax))
