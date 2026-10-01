"""Spec 48: DB engine provisioning and request.db bridge."""

from __future__ import annotations

import sqlite3

import pytest
from pyramid.scripting import prepare

from namifax.db.engine import DatabaseEngine


# --- 2.1 resolve_database_url -------------------------------------------------

def test_url_prefers_settings_over_env():
    from namifax.db.provider import resolve_database_url

    env = {"DATABASE_URL": "sqlite:///env.db", "AFDB_URL": "sqlite:///afdb.db"}
    assert resolve_database_url({"sqlalchemy.url": "sqlite:///s.db"}, env) == "sqlite:///s.db"


def test_url_database_url_beats_afdb_url():
    from namifax.db.provider import resolve_database_url

    env = {"DATABASE_URL": "sqlite:///env.db", "AFDB_URL": "sqlite:///afdb.db"}
    assert resolve_database_url({}, env) == "sqlite:///env.db"
    assert resolve_database_url({}, {"AFDB_URL": "sqlite:///afdb.db"}) == "sqlite:///afdb.db"


def test_url_falls_back_to_namifax_db_path():
    from namifax.db.provider import resolve_database_url

    assert resolve_database_url({}, {"NAMIFAX_DB_PATH": "/x/y.db"}) == "sqlite:////x/y.db"


def test_url_default_is_cwd_namifax_db(tmp_path, monkeypatch):
    from namifax.db.provider import resolve_database_url

    monkeypatch.chdir(tmp_path)
    url = resolve_database_url({}, {})
    assert url == f"sqlite:///{tmp_path.resolve() / 'namifax.db'}" or url.endswith("/namifax.db")


# --- 2.2 create_sa_engine -----------------------------------------------------

def test_memory_engine_shares_one_database_across_connections():
    from namifax.db.provider import create_sa_engine

    engine = create_sa_engine("sqlite://")
    c1 = engine.raw_connection()
    c1.driver_connection.execute("CREATE TABLE t (a INTEGER)")
    c1.driver_connection.execute("INSERT INTO t VALUES (1)")
    c1.driver_connection.commit()
    c2 = engine.raw_connection()
    assert c2.driver_connection.execute("SELECT a FROM t").fetchall() == [(1,)]


# --- 2.3 DatabaseEngine.from_connection --------------------------------------

def test_from_connection_returns_dict_records_without_row_factory():
    raw = sqlite3.connect(":memory:")  # row_factory 기본(tuple)
    db = DatabaseEngine.from_connection(raw)
    assert db.query("CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT)").executed
    assert db.query("INSERT INTO t (name) VALUES (?)", ["a"]).executed
    assert db.query("SELECT id, name FROM t").executed
    assert db.get_records() == [{"id": 1, "name": "a"}]


def test_from_connection_disconnect_closes_wrapped_connection():
    raw = sqlite3.connect(":memory:")
    db = DatabaseEngine.from_connection(raw)
    db.disconnect()
    with pytest.raises(sqlite3.ProgrammingError):
        raw.execute("SELECT 1")


# --- 2.4 / 2.5 create_app + request.db ---------------------------------------

def _make_app(db_file):
    from namifax import create_app

    return create_app(**{"sqlalchemy.url": f"sqlite:///{db_file}"})


def test_registry_holds_engine_and_tables_are_initialised(tmp_path):
    app = _make_app(tmp_path / "a.db")
    assert app.registry["dbengine"] is not None
    env = prepare(registry=app.registry)
    db = env["request"].db
    assert db.query("SELECT COUNT(*) AS n FROM sqlite_master WHERE name='UserAccount'").executed
    assert db.get_records()[0]["n"] == 1
    env["closer"]()


def test_two_apps_with_different_urls_are_isolated(tmp_path):
    app1 = _make_app(tmp_path / "one.db")
    app2 = _make_app(tmp_path / "two.db")

    e1 = prepare(registry=app1.registry)
    e1["request"].db.query("CREATE TABLE probe (v INTEGER)")
    e1["request"].db.query("INSERT INTO probe VALUES (1)")

    e2 = prepare(registry=app2.registry)
    res = e2["request"].db.query("SELECT * FROM probe")
    assert not res.executed  # app2 에는 probe 테이블이 없다
    e1["closer"]()
    e2["closer"]()


def test_request_db_is_reified_and_released_on_finish(tmp_path):
    app = _make_app(tmp_path / "a.db")
    env = prepare(registry=app.registry)
    request = env["request"]
    assert request.db is request.db
    db = request.db
    env["closer"]()
    assert db._conn is None  # disconnect() 로 풀에 반환됨
