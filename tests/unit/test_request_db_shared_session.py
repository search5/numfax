"""B0-5: under pyramid_tm, request.db shares the session's connection and transaction."""

from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock

import pytest
import webtest
from pyramid.config import Configurator
from pyramid.scripting import prepare
from sqlalchemy import text

from namifax.db.engine import DatabaseEngine
from namifax.db.provider import create_sa_engine, open_db
from namifax.db.schema import init_database_tables


def _rows(db_file, key):
    con = sqlite3.connect(db_file)
    try:
        return con.execute("SELECT value FROM SystemConfig WHERE key = ?", (key,)).fetchall()
    finally:
        con.close()


# --- DatabaseEngine managed mode (unit) -----------------------------------------------

def _managed(conn=None, on_change=None):
    import sqlite3 as sq

    raw = conn or sq.connect(":memory:")
    raw.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    return raw, DatabaseEngine.from_connection(raw, managed=True, on_change=on_change)


def test_managed_engine_never_commits_or_closes_the_connection():
    raw = MagicMock()
    cursor = raw.cursor.return_value
    cursor.rowcount, cursor.lastrowid = 1, 7
    db = DatabaseEngine.from_connection(raw, managed=True)
    assert db.query("INSERT INTO t (v) VALUES ('a')").executed
    raw.commit.assert_not_called()
    db.disconnect()
    raw.close.assert_not_called()
    assert db._conn is None


def test_managed_engine_reports_changes_only_for_successful_writes():
    changes = []
    _, db = _managed(on_change=lambda: changes.append(1))
    db.query("INSERT INTO t (v) VALUES ('a')")
    db.query("SELECT * FROM t")
    assert changes == [1]
    assert not db.query("INSERT INTO missing (v) VALUES ('a')").executed
    assert changes == [1]


def test_managed_engine_transaction_context_leaves_commit_to_the_owner():
    raw = MagicMock()
    db = DatabaseEngine.from_connection(raw, managed=True)
    with db.transaction():
        pass
    raw.commit.assert_not_called()
    with pytest.raises(ValueError):
        with db.transaction():
            raise ValueError("boom")
    raw.rollback.assert_not_called()


def test_unmanaged_engine_still_commits_each_write():
    raw = MagicMock()
    raw.cursor.return_value.rowcount = 1
    db = DatabaseEngine.from_connection(raw)
    db.query("INSERT INTO t (v) VALUES ('a')")
    raw.commit.assert_called_once()


# --- request.db wiring -----------------------------------------------------------------

@pytest.fixture
def app_and_file(tmp_path):
    from namifax import create_app

    db_file = tmp_path / "shared.db"
    return create_app(**{"sqlalchemy.url": f"sqlite:///{db_file}"}), db_file


def _active_request(app):
    """A request as the pyramid_tm tween presents it: manager begun, tm.active set."""
    env = prepare(registry=app.registry)
    request = env["request"]
    request.environ["tm.active"] = True
    request.tm.begin()
    return env, request


def test_db_writes_are_visible_to_dbsession_and_committed_with_the_transaction(app_and_file):
    app, db_file = app_and_file
    env, request = _active_request(app)
    try:
        request.db.query("INSERT INTO SystemConfig (key, value) VALUES ('s1', 'raw')")
        assert _rows(db_file, "s1") == []  # not committed yet: other connections do not see it
        seen = request.dbsession.execute(text("SELECT value FROM SystemConfig WHERE key = 's1'")).scalar()
        assert seen == "raw"  # same transaction: the ORM session sees the raw write
        request.tm.commit()
    finally:
        env["closer"]()
    assert _rows(db_file, "s1") == [("raw",)]


def test_db_writes_are_rolled_back_with_the_transaction(app_and_file):
    app, db_file = app_and_file
    env, request = _active_request(app)
    try:
        request.db.query("INSERT INTO SystemConfig (key, value) VALUES ('s2', 'raw')")
        request.tm.abort()
    finally:
        env["closer"]()
    assert _rows(db_file, "s2") == []


def test_finishing_the_request_does_not_close_the_session_connection(app_and_file):
    app, _ = app_and_file
    env, request = _active_request(app)
    db = request.db
    request.dbsession.execute(text("SELECT 1"))
    request._process_finished_callbacks()
    assert db._conn is None
    assert request.dbsession.execute(text("SELECT 1")).scalar() == 1
    request.tm.abort()
    env["closer"]()


def test_without_the_tween_request_db_keeps_the_standalone_commit_per_write_behaviour(app_and_file):
    app, db_file = app_and_file
    with prepare(registry=app.registry) as env:
        env["request"].db.query("INSERT INTO SystemConfig (key, value) VALUES ('s3', 'raw')")
        assert _rows(db_file, "s3") == [("raw",)]


# --- through the real tween ------------------------------------------------------------

@pytest.fixture
def tween_app(tmp_path):
    db_file = tmp_path / "tween.db"
    engine = create_sa_engine(f"sqlite:///{db_file}")
    boot = open_db(engine)
    init_database_tables(boot)
    boot.disconnect()

    def ok(request):
        request.db.query("INSERT INTO SystemConfig (key, value) VALUES ('ok', 'committed')")
        return {"ok": True}

    def boom(request):
        request.db.query("INSERT INTO SystemConfig (key, value) VALUES ('boom', 'rolled-back')")
        raise RuntimeError("view failed")

    with Configurator(settings={"dbengine": engine}) as config:
        config.include("namifax.models")
        config.add_route("ok", "/ok")
        config.add_route("boom", "/boom")
        config.add_view(ok, route_name="ok", renderer="json")
        config.add_view(boom, route_name="boom", renderer="json")
        app = config.make_wsgi_app()
    return webtest.TestApp(app), db_file


def test_request_db_writes_are_committed_when_the_request_succeeds(tween_app):
    client, db_file = tween_app
    client.get("/ok", status=200)
    assert _rows(db_file, "ok") == [("committed",)]


def test_request_db_writes_are_rolled_back_when_the_view_raises(tween_app):
    client, db_file = tween_app
    with pytest.raises(RuntimeError, match="view failed"):
        client.get("/boom")
    assert _rows(db_file, "boom") == []


def test_real_application_commits_raw_writes_made_during_a_request(tmp_path):
    """Login (raw UPDATE of last_login) and the admin SMTP form (raw INSERT/UPDATE) persist."""
    from namifax import create_app

    db_file = tmp_path / "e2e.db"
    client = webtest.TestApp(create_app(**{"sqlalchemy.url": f"sqlite:///{db_file}"}))

    client.post("/login", {"username": "admin", "password": "password", "_submit_check": "1"}, status=302)
    client.post("/admin/smtp", {
        "action": "save", "smtp_host": "smtp.shared.test", "smtp_port": "2525",
        "smtp_security": "NONE", "from_email": "fax@shared.test",
    }, status=302)

    con = sqlite3.connect(db_file)
    try:
        assert con.execute("SELECT smtp_host FROM SystemSettings WHERE id = 1").fetchone() == ("smtp.shared.test",)
        assert con.execute("SELECT last_login FROM UserAccount WHERE username = 'admin'").fetchone()[0]
    finally:
        con.close()
