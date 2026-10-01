"""cli_unit(): one connection shared by the legacy DatabaseEngine and an ORM Session for a command-line run."""

from __future__ import annotations

import sqlite3

import pytest
from sqlalchemy import text

from namifax.db.engine import DatabaseEngine


def _env(tmp_path, name="u.db"):
    return {"DATABASE_URL": f"sqlite:///{tmp_path / name}"}


def _count(path, sql):
    con = sqlite3.connect(path)
    try:
        return con.execute(sql).fetchone()[0]
    finally:
        con.close()


def test_the_unit_offers_an_engine_and_a_session_on_a_schema_ready_database(tmp_path):
    from namifax.db.provider import cli_unit

    with cli_unit(environ=_env(tmp_path)) as unit:
        assert isinstance(unit.db, DatabaseEngine)
        assert unit.session.execute(text("SELECT COUNT(*) FROM UserAccount")).scalar() >= 1
        assert unit.db.query("SELECT COUNT(*) AS n FROM UserAccount").executed


def test_both_sides_see_each_others_uncommitted_writes(tmp_path):
    from namifax.db.provider import cli_unit

    with cli_unit(environ=_env(tmp_path)) as unit:
        unit.db.query("INSERT INTO SystemConfig (key, value) VALUES ('raw', '1')")
        assert unit.session.execute(text("SELECT value FROM SystemConfig WHERE key = 'raw'")).scalar() == "1"
        unit.session.execute(text("INSERT INTO SystemConfig (key, value) VALUES ('orm', '2')"))
        unit.db.query("SELECT value FROM SystemConfig WHERE key = 'orm'")
        assert unit.db.get_records() == [{"value": "2"}]


def test_nothing_is_visible_to_other_connections_until_the_unit_ends(tmp_path):
    from namifax.db.provider import cli_unit

    path = tmp_path / "u.db"
    with cli_unit(environ=_env(tmp_path)) as unit:
        unit.db.query("INSERT INTO SystemConfig (key, value) VALUES ('k', 'v')")
        unit.session.execute(text("INSERT INTO SystemConfig (key, value) VALUES ('k2', 'v2')"))
        assert _count(path, "SELECT COUNT(*) FROM SystemConfig WHERE key IN ('k', 'k2')") == 0
    assert _count(path, "SELECT COUNT(*) FROM SystemConfig WHERE key IN ('k', 'k2')") == 2


def test_an_orm_write_followed_by_a_legacy_write_does_not_lock_the_database(tmp_path):
    """Two writing connections would block each other on SQLite; one shared connection cannot."""
    from namifax.db.provider import cli_unit

    with cli_unit(environ=_env(tmp_path)) as unit:
        unit.session.execute(text("INSERT INTO SystemConfig (key, value) VALUES ('a', '1')"))
        assert unit.db.query("INSERT INTO SysLog (logdate, logtext) VALUES ('2026-10-01 10:00:00', 'x')").executed
        unit.session.execute(text("INSERT INTO SystemConfig (key, value) VALUES ('b', '2')"))


def test_everything_is_rolled_back_when_the_run_fails(tmp_path):
    from namifax.db.provider import cli_unit

    path = tmp_path / "u.db"
    with pytest.raises(RuntimeError):
        with cli_unit(environ=_env(tmp_path)) as unit:
            unit.db.query("INSERT INTO SystemConfig (key, value) VALUES ('raw', '1')")
            unit.session.execute(text("INSERT INTO SystemConfig (key, value) VALUES ('orm', '2')"))
            raise RuntimeError("hook failed")
    assert _count(path, "SELECT COUNT(*) FROM SystemConfig WHERE key IN ('raw', 'orm')") == 0


def test_orm_flushes_are_part_of_the_commit(tmp_path):
    from namifax.db.provider import cli_unit
    from namifax.models import SystemConfig

    with cli_unit(environ=_env(tmp_path)) as unit:
        unit.session.add(SystemConfig(key="obj", value="v"))  # flushed by the unit when it ends
    assert _count(tmp_path / "u.db", "SELECT COUNT(*) FROM SystemConfig WHERE key = 'obj'") == 1


def test_settings_beat_the_environment_and_the_schema_can_be_skipped(tmp_path):
    from namifax.db.provider import cli_unit

    app_file, env_file = tmp_path / "app.db", tmp_path / "env.db"
    with cli_unit({"sqlalchemy.url": f"sqlite:///{app_file}"}, environ={"DATABASE_URL": f"sqlite:///{env_file}"},
                  ensure_schema=False) as unit:
        assert not unit.db.query("SELECT 1 FROM UserAccount").executed  # no tables were created
    assert app_file.exists() and not env_file.exists()


def test_the_engine_never_commits_or_closes_the_shared_connection_itself(tmp_path):
    from namifax.db.provider import cli_unit

    with cli_unit(environ=_env(tmp_path)) as unit:
        unit.db.disconnect()  # a service releasing its engine must not break the session
        assert unit.session.execute(text("SELECT 1")).scalar() == 1
