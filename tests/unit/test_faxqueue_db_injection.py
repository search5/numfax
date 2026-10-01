"""Spec 48 loop V11: FaxQueue receives a DatabaseEngine and its callers pass request.db."""

from __future__ import annotations

import contextlib
from unittest.mock import MagicMock, patch

from pyramid import testing

from namifax.services.faxqueue import FaxQueue
from namifax.views import ajax as ajax_mod
from namifax.views import modals as modals_mod
from namifax.views import outbox as outbox_mod


class _Request(testing.DummyRequest):
    identity = {"username": "admin", "uid": 1, "is_admin": True, "superuser": True}


def _request(method="GET", params=None):
    req = _Request()
    req.db = object()
    req.method = method
    req.params = params or {}
    req.POST = req.params
    req.session = {"user_id": 1, "username": "admin", "is_admin": True, "superuser": True}
    req.route_url = MagicMock(return_value="/x")
    return req


def test_faxqueue_resolves_users_with_injected_db():
    db = object()
    fq = FaxQueue(auto_process=False, db=db)
    with patch("namifax.services.faxqueue.AFUserAccount") as cls:
        fq.get_queue()
        fq.list_owner("admin")
    assert cls.call_args_list
    for call in cls.call_args_list:
        assert call.kwargs.get("db") is db


def _assert_queue_built_with_db(mod, view, req):
    cls = MagicMock(name="FaxQueue")
    with patch.object(mod, "FaxQueue", cls), \
            patch.object(mod, "get_all_admin_modems", MagicMock(return_value=[]), create=True), \
            contextlib.suppress(Exception):
        view(req)
    assert cls.call_args_list, "FaxQueue was never built"
    for call in cls.call_args_list:
        assert call.kwargs.get("db") is req.db


def test_ajax_faxalter_builds_queue_with_request_db():
    _assert_queue_built_with_db(ajax_mod, ajax_mod.ajax_faxalter, _request("POST", {"jid": "1", "priority": "100"}))


def test_modal_refax_builds_queue_with_request_db():
    req = _request("POST", {"fid": "1", "destinations": "555", "_submit_check": "1"})
    _assert_queue_built_with_db(modals_mod, modals_mod.modal_refax_view, req)


def test_outbox_builds_queue_with_request_db():
    _assert_queue_built_with_db(outbox_mod, outbox_mod.outbox_view, _request())
