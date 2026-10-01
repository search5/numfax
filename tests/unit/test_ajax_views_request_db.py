"""Spec 48 loop V3: views/ajax.py hands request.db to every domain object it builds."""

from __future__ import annotations

import contextlib
from unittest.mock import MagicMock, patch

import pytest
from pyramid import testing

from namifax.views import ajax as ajax_mod

CASES = [
    ("ajax_modem_status", "GET", {}),
    ("ajax_inbox_count", "GET", {}),
    ("ajax_addressbook_suggest", "GET", {"q": "a"}),
    ("ajax_emailbook_suggest", "GET", {"q": "a"}),
    ("ajax_addressbook_prefill", "GET", {"cid": "1", "faxnumid": "1"}),
    ("ajax_distrolist_faxes", "GET", {"dlid": "1"}),
    ("ajax_archive_fax", "POST", {"fid": "1"}),
    ("ajax_deletefaxes_view", "POST", {"fids": "1,2"}),
    ("ajax_archivebook_view", "GET", {"q": "a"}),
]
CLASSES = ["ArchiveIn", "AFAddressBook", "FaxModem", "DistributionList"]


@pytest.mark.parametrize("name,method,params", CASES, ids=[c[0] for c in CASES])
def test_view_builds_domain_objects_with_request_db(name, method, params):
    req = testing.DummyRequest()
    req.session = {"user_id": 1, "username": "admin", "is_admin": True, "superuser": True}
    req.db = object()
    req.method = method
    req.params = params

    mocks = {c: MagicMock(name=c) for c in CLASSES}
    modems = MagicMock(return_value=[{"device": "ttyS0", "status": "Idle"}])
    with patch.multiple(ajax_mod, **mocks), \
            patch.object(ajax_mod, "get_all_admin_modems", modems), \
            contextlib.suppress(Exception):
        getattr(ajax_mod, name)(req)

    calls = [c for m in mocks.values() for c in m.call_args_list]
    calls += list(modems.call_args_list)
    assert calls, f"{name} built no domain objects"
    for call in calls:
        passed = call.kwargs.get("db", call.args[0] if call.args else None)
        assert passed is req.db, f"{name}: built without request.db"
