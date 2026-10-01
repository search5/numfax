"""Spec 48 loop V1: views/inbox.py hands request.db to every domain object it builds."""

from __future__ import annotations

import contextlib
import sqlite3
from unittest.mock import MagicMock, patch

import pytest
from pyramid import testing
from pyramid.scripting import prepare

from namifax.views import inbox as inbox_mod


def _request(**kw):
    req = testing.DummyRequest(**kw)
    req.db = object()
    return req


VIEW_CASES = [
    ("inbox_view", {}, {}),
    ("viewfax_view", {"params": {"fid": "1"}}, {}),
    ("fax_download_view", {"params": {"format": "pdf"}}, {"matchdict": {"fid": "1"}}),
    ("fax_rotate_view", {"params": {}}, {"matchdict": {"fid": "1"}}),
    ("setcompany_view", {"params": {"fid": "1", "faxnumid": "1"}}, {}),
]


@pytest.mark.parametrize("name,kwargs,attrs", VIEW_CASES, ids=[c[0] for c in VIEW_CASES])
def test_view_builds_domain_objects_with_request_db(name, kwargs, attrs):
    req = _request(**kwargs)
    for k, v in attrs.items():
        setattr(req, k, v)
    arc_cls, ab_cls = MagicMock(name="ArchiveIn"), MagicMock(name="AFAddressBook")
    with patch.object(inbox_mod, "ArchiveIn", arc_cls), \
            patch.object(inbox_mod, "AFAddressBook", ab_cls), \
            patch.object(inbox_mod, "get_all_admin_modems", MagicMock(return_value=[])), \
            contextlib.suppress(Exception):
        getattr(inbox_mod, name)(req)

    assert arc_cls.called, f"{name} did not build ArchiveIn"
    for cls in (arc_cls, ab_cls):
        for call in cls.call_args_list:
            assert call.kwargs.get("db") is req.db, f"{name}: {cls._mock_name} built without request.db"


def test_inbox_view_lists_rows_from_the_app_database_not_the_global_one(tmp_path):
    from namifax import create_app

    db_file = tmp_path / "isolated.db"
    app = create_app(**{"sqlalchemy.url": f"sqlite:///{db_file}"})
    con = sqlite3.connect(db_file)
    try:
        con.execute("UPDATE FaxArchive SET company='Isolated Co', companyid=NULL, faxnumid=NULL")
        con.commit()
    finally:
        con.close()

    env = prepare(registry=app.registry)
    try:
        res = inbox_mod.inbox_view(env["request"])
    finally:
        env["closer"]()

    assert res["total_faxes"] >= 1
    assert {f["company"] for f in res["faxes"]} == {"Isolated Co"}
