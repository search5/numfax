"""Spec 48 loop V4: views/admin.py (domain admin pages) hands request.db to every object it builds."""

from __future__ import annotations

import contextlib
from unittest.mock import MagicMock, patch

import pytest
from pyramid import testing

from namifax.views import admin as admin_mod

# (patch target, name) — local imports are patched at the source module, module-level ones on admin
SERVICE_TARGETS = [
    "namifax.services.user_account.AFUserAccount",
    "namifax.services.modem.FaxModem",
    "namifax.services.addressbook.AFAddressBook",
    "namifax.views.admin.DIDRouting",
    "namifax.views.admin.FaxPDFCategory",
    "namifax.views.admin.Covers",
    "namifax.views.admin.BarcodeRouting",
    "namifax.views.admin.DynamicConfig",
    "namifax.services.categories.FaxPDFCategory",
]
HELPERS = ["get_all_admin_users", "get_all_admin_modems", "get_all_syslogs"]

CASES = [
    ("admin_dashboard_view", "GET", {}),
    ("admin_users_view", "GET", {}),
    ("admin_users_view", "POST", {"delete": "1", "uid": "2"}),
    ("admin_users_view", "POST", {"name": "N", "username": "u", "password": "p"}),
    ("admin_modems_view", "GET", {}),
    ("admin_modems_view", "POST", {"delete": "1", "devid": "1"}),
    ("admin_modems_view", "POST", {"device": "ttyS1", "alias": "a"}),
    ("admin_routing_did_view", "GET", {}),
    ("admin_system_logs_view", "GET", {}),
    ("admin_covers_view", "GET", {}),
    ("admin_categories_view", "GET", {}),
    ("admin_barcodes_view", "GET", {}),
    ("admin_dynconf_view", "GET", {}),
    ("admin_fax2email_view", "GET", {}),
]


@pytest.mark.parametrize("name,method,params", CASES, ids=[f"{c[0]}-{c[1]}-{i}" for i, c in enumerate(CASES)])
def test_view_builds_domain_objects_with_request_db(name, method, params):
    req = testing.DummyRequest()
    req.__dict__["identity"] = {"username": "admin", "uid": 1, "is_admin": True, "superuser": True}
    req.db = object()
    req.dbsession = object()
    req.method = method
    req.params = params
    req.route_url = MagicMock(return_value="/x")

    with contextlib.ExitStack() as stack:
        classes = [stack.enter_context(patch(t)) for t in dict.fromkeys(SERVICE_TARGETS)]
        helpers = {h: stack.enter_context(patch.object(admin_mod, h, MagicMock(return_value=[]))) for h in HELPERS}
        with contextlib.suppress(Exception):
            getattr(admin_mod, name)(req)

    for target, cls in zip(dict.fromkeys(SERVICE_TARGETS), classes):
        # ORM-backed services take the request session, the others the legacy request.db
        expected = req.dbsession if target.endswith("FaxPDFCategory") else req.db
        for call in cls.call_args_list:
            assert call.kwargs.get("db") is expected, f"{name}: {target} built with the wrong database"
    for hname, helper in helpers.items():
        for call in helper.call_args_list:
            if hname == "get_all_syslogs":  # ORM-backed: takes the request session
                assert call.kwargs.get("session") is req.dbsession, f"{name}: {hname} called without request.dbsession"
                continue
            passed = call.kwargs.get("db", call.args[0] if call.args else None)
            assert passed is req.db, f"{name}: {hname} called without request.db"
    assert any(c.call_args_list for c in classes) or any(h.call_args_list for h in helpers.values()), \
        f"{name} used no domain objects"


def test_get_all_admin_users_uses_given_db():
    db = object()
    with patch("namifax.services.user_account.AFUserAccount") as cls:
        cls.return_value.list_accounts.return_value = []
        admin_mod.get_all_admin_users(db)
    assert cls.call_args.kwargs.get("db") is db

