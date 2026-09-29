"""AvantFAX Web Admin view handler."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from avantfax.services.barcode import BarcodeRouting
from avantfax.services.categories import FaxPDFCategory
from avantfax.services.covers import Covers
from avantfax.services.did import DIDRouting
from avantfax.services.dynconf import DynamicConfig
from avantfax.services.modem import FaxModem
from avantfax.services.user_account import AFUserAccount


class AdminHandler:
    """Handles system administration, modem/routing configuration, and user accounts."""

    def list_users(self) -> List[Dict[str, Any]]:
        """List all registered users."""
        user_svc = AFUserAccount()
        users = []
        for u in (user_svc.list_accounts() or []):
            if isinstance(u, dict):
                users.append({
                    "uid": u.get("uid"),
                    "username": u.get("username"),
                    "name": u.get("name"),
                    "email": u.get("email"),
                    "is_admin": bool(u.get("is_admin", False)),
                    "superuser": bool(u.get("superuser", False)),
                })
            else:
                users.append({
                    "uid": getattr(u, "uid", None),
                    "username": getattr(u, "username", None),
                    "name": getattr(u, "name", None),
                    "email": getattr(u, "email", None),
                    "is_admin": getattr(u, "is_admin", False),
                    "superuser": getattr(u, "superuser", False),
                })
        return users

    def save_user(self, user_data: Dict[str, Any]) -> bool:
        """Create or update user account."""
        user_svc = AFUserAccount()
        uid = user_data.get("uid")
        if uid and user_svc.load(int(uid)):
            for k in ("username", "name", "email", "is_admin", "superuser"):
                if k in user_data:
                    user_svc.dbdata[k] = user_data[k]
            return user_svc.update()
        return user_svc.create(user_data)

    def delete_user(self, uid: int) -> bool:
        """Delete user account."""
        user_svc = AFUserAccount()
        return user_svc.remove(int(uid))

    def list_modems(self) -> List[Dict[str, Any]]:
        """List all modem devices."""
        modem_svc = FaxModem()
        modems = []
        for dev in modem_svc.get_modems():
            if modem_svc.load_device(dev):
                modems.append({
                    "device": dev,
                    "alias": modem_svc.get_alias(),
                    "contact": modem_svc.get_contact(),
                    "printer": modem_svc.get_printer(),
                    "faxcatid": modem_svc.get_faxcatid(),
                })
        return modems

    def save_modem(
        self,
        device: str,
        alias: str,
        contact: Optional[str] = None,
        printer: Optional[str] = None,
        faxcatid: Optional[int] = None,
    ) -> bool:
        """Create or update modem settings."""
        modem_svc = FaxModem()
        if modem_svc.load_device(device):
            return modem_svc.update_settings(alias, contact, printer, faxcatid)
        return modem_svc.create(device, alias, contact, printer, faxcatid)

    def list_did_routes(self) -> List[Dict[str, Any]]:
        """List all DID routes."""
        did_svc = DIDRouting()
        routes = []
        for r in did_svc.get_routes():
            if did_svc.load_route(r):
                routes.append({
                    "didr_id": did_svc.get_didr_id(),
                    "routecode": r,
                    "alias": did_svc.get_alias(),
                    "contact": did_svc.get_contact(),
                    "printer": did_svc.get_printer(),
                    "faxcatid": did_svc.get_faxcatid(),
                })
        return routes

    def save_did_route(
        self,
        routecode: str,
        alias: str,
        contact: Optional[str] = None,
        printer: Optional[str] = None,
        faxcatid: Optional[int] = None,
    ) -> bool:
        """Create or update DID route."""
        did_svc = DIDRouting()
        if did_svc.load_route(routecode):
            return did_svc.update_settings(alias, contact, printer, faxcatid)
        return did_svc.create(routecode, alias, contact, printer, faxcatid)

    def list_dynconf(self) -> List[Dict[str, Any]]:
        """List all blacklist entries in DynConf."""
        dc = DynamicConfig()
        return dc.get_dynconf() or []

    def add_dynconf(self, device: str, callid: str) -> bool:
        """Add blacklist entry to DynConf."""
        dc = DynamicConfig()
        return dc.create(device, callid)

    def list_categories(self) -> List[Dict[str, Any]]:
        """List all fax categories."""
        cat_svc = FaxPDFCategory()
        cats = cat_svc.get_categories() or {}
        return [{"catid": k, "name": v} for k, v in cats.items()]

    def save_category(self, catid: Optional[int], name: str) -> bool:
        """Create or rename fax category."""
        cat_svc = FaxPDFCategory()
        if catid and cat_svc.load_category(catid):
            return cat_svc.rename(name)
        return cat_svc.create(name)
