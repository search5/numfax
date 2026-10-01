"""Spec 48 loop V7: views/addressbook.py hands request.db to every domain object it builds."""

from __future__ import annotations

import contextlib
from unittest.mock import MagicMock, patch

import pytest
from pyramid import testing

from namifax.views import addressbook as mod

CASES = [
    ("addressbook_list_view", "GET", {}),
    ("addressbook_edit_view", "GET", {}),
    ("addressbook_edit_view", "POST", {"delete": "1", "company_id": "1"}),
    ("addressbook_edit_view", "POST", {"company": "C", "company_id": "1", "faxnumber": "555"}),
    ("addressbook_edit_view", "POST", {"company": "C"}),
    ("emailbook_list_view", "GET", {}),
    ("emailbook_edit_view", "GET", {}),
    ("emailbook_edit_view", "POST", {"delete": "1", "email_id": "1"}),
    ("emailbook_edit_view", "POST", {"contact_name": "n", "contact_email": "a@x.test", "company": "C"}),
]


@pytest.mark.parametrize("name,method,params", CASES, ids=[f"{c[0]}-{c[1]}-{i}" for i, c in enumerate(CASES)])
def test_view_builds_domain_objects_with_request_db(name, method, params):
    req = testing.DummyRequest()
    req.__dict__["identity"] = {"username": "admin", "uid": 1, "is_admin": True, "superuser": True}
    req.db = object()
    req.method = method
    req.params = params
    req.route_url = MagicMock(return_value="/x")

    cls = MagicMock(name="AFAddressBook")
    cls.return_value.get_companies.return_value = []
    with patch.object(mod, "AFAddressBook", cls), contextlib.suppress(Exception):
        getattr(mod, name)(req)

    assert cls.call_args_list, f"{name} built no AFAddressBook"
    for call in cls.call_args_list:
        assert call.kwargs.get("db") is req.db, f"{name}: built without request.db"


def test_get_all_companies_uses_given_db():
    db = object()
    with patch.object(mod, "AFAddressBook") as cls:
        cls.return_value.get_companies.return_value = []
        mod.get_all_companies(db)
    assert cls.call_args.kwargs.get("db") is db
