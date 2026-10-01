"""P3: every test runs against its own database, never the working-tree namifax.db."""

from __future__ import annotations

import os

import namifax.db.engine as engine_mod
from namifax.db.provider import cli_db, resolve_database_url


def test_default_database_url_is_not_the_working_tree_file():
    url = resolve_database_url({}, os.environ)
    assert url != f"sqlite:///{os.path.join(os.getcwd(), 'namifax.db')}"
    assert os.getcwd() not in url.replace("sqlite:///", "")


def test_cli_db_does_not_touch_the_working_tree_database():
    path = os.path.join(os.getcwd(), "namifax.db")
    before = os.stat(path).st_mtime_ns if os.path.exists(path) else None
    with cli_db() as db:
        assert db.query("SELECT COUNT(*) AS n FROM UserAccount").executed
    after = os.stat(path).st_mtime_ns if os.path.exists(path) else None
    assert before == after


def test_legacy_default_engine_is_isolated_and_reset():
    assert engine_mod._DEFAULT_ENGINE is None
    engine = engine_mod.get_default_engine()
    assert engine is engine_mod._DEFAULT_ENGINE
