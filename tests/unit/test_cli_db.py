"""Spec 48 loop C0: cli_db() opens the configured database for command-line entry points."""

from __future__ import annotations

import sqlite3

import namifax.db.engine as engine_mod
from namifax.db.engine import DatabaseEngine


def test_cli_db_uses_env_url_and_ensures_schema(tmp_path, monkeypatch):
    from namifax.db.provider import cli_db

    monkeypatch.setattr(engine_mod, "_DEFAULT_ENGINE", None)
    db_file = tmp_path / "cli.db"
    with cli_db(environ={"DATABASE_URL": f"sqlite:///{db_file}"}) as db:
        assert isinstance(db, DatabaseEngine)
        assert db.query("SELECT COUNT(*) AS n FROM UserAccount").executed
    assert engine_mod._DEFAULT_ENGINE is None

    con = sqlite3.connect(db_file)
    try:
        assert con.execute("SELECT COUNT(*) FROM UserAccount").fetchone()[0] >= 1
    finally:
        con.close()


def test_cli_db_settings_override_environment(tmp_path):
    from namifax.db.provider import cli_db

    settings_file, env_file = tmp_path / "s.db", tmp_path / "e.db"
    with cli_db({"sqlalchemy.url": f"sqlite:///{settings_file}"},
                environ={"DATABASE_URL": f"sqlite:///{env_file}"}):
        pass
    assert settings_file.exists() and not env_file.exists()


def test_cli_db_releases_connection_on_exit_and_on_error(tmp_path):
    from namifax.db.provider import cli_db

    url = {"DATABASE_URL": f"sqlite:///{tmp_path / 'c.db'}"}
    with cli_db(environ=url) as db:
        pass
    assert db._conn is None

    try:
        with cli_db(environ=url) as db2:
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    assert db2._conn is None


def test_cli_db_can_skip_schema_creation(tmp_path):
    from namifax.db.provider import cli_db

    with cli_db(environ={"DATABASE_URL": f"sqlite:///{tmp_path / 'n.db'}"}, ensure_schema=False) as db:
        assert not db.query("SELECT 1 FROM UserAccount").executed
