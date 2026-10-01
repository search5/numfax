"""B0-6: the Alembic baseline creates SystemConfig portably and coexists with the legacy SQLite schema."""

from __future__ import annotations

import re
import shutil
import sqlite3
from pathlib import Path

import alembic.command
import alembic.config
import pytest
import sqlalchemy as sa

ROOT = Path(__file__).resolve().parents[2]
PKG_ALEMBIC = ROOT / "src" / "namifax" / "alembic"


def _cfg(tmp_path: Path) -> alembic.config.Config:
    scripts = tmp_path / "alembic"
    shutil.copytree(PKG_ALEMBIC, scripts)
    ini = re.sub(r"(?m)^script_location\s*=.*$", f"script_location = {scripts}", (ROOT / "development.ini").read_text())
    ini_path = tmp_path / "mig.ini"
    ini_path.write_text(ini)
    return alembic.config.Config(str(ini_path))


def _columns(engine, table):
    return {c["name"]: c for c in sa.inspect(engine).get_columns(table)}


def test_upgrade_creates_the_table_on_an_empty_database(tmp_path, monkeypatch):
    db_file = tmp_path / "fresh.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    alembic.command.upgrade(_cfg(tmp_path), "head")

    engine = sa.create_engine(f"sqlite:///{db_file}")
    cols = _columns(engine, "SystemConfig")
    assert set(cols) == {"key", "value"}
    assert cols["key"]["nullable"] is False and cols["value"]["nullable"] is True
    assert sa.inspect(engine).get_pk_constraint("SystemConfig")["constrained_columns"] == ["key"]
    engine.dispose()


def test_upgrade_is_a_noop_for_a_table_the_legacy_schema_already_created(tmp_path, monkeypatch):
    from namifax.db.engine import DatabaseEngine
    from namifax.db.schema import init_database_tables

    db_file = tmp_path / "legacy.db"
    legacy = DatabaseEngine()
    assert legacy.connect_sqlite(str(db_file))
    init_database_tables(legacy)
    legacy.query("INSERT INTO SystemConfig (key, value) VALUES ('keep', 'me')")
    legacy.disconnect()

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    alembic.command.upgrade(_cfg(tmp_path), "head")

    con = sqlite3.connect(db_file)
    try:
        assert con.execute("SELECT value FROM SystemConfig WHERE key = 'keep'").fetchone() == ("me",)
        assert con.execute("SELECT COUNT(*) FROM alembic_version").fetchone() == (1,)
    finally:
        con.close()


def test_downgrade_removes_the_table(tmp_path, monkeypatch):
    db_file = tmp_path / "down.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    cfg = _cfg(tmp_path)
    alembic.command.upgrade(cfg, "head")
    alembic.command.downgrade(cfg, "base")

    engine = sa.create_engine(f"sqlite:///{db_file}")
    assert not sa.inspect(engine).has_table("SystemConfig")
    engine.dispose()


def test_there_is_exactly_one_head_revision(tmp_path):
    from alembic.script import ScriptDirectory

    assert len(ScriptDirectory.from_config(_cfg(tmp_path)).get_heads()) == 1


# --- real servers (optional): PostgreSQL, MySQL and MariaDB, see tests/conftest.py ---------------

@pytest.mark.serverdb
def test_server_database_baseline_and_orm_upsert(tmp_path, monkeypatch, server_db_url):
    from sqlalchemy.orm import Session

    from namifax.models import SystemConfig
    from namifax.services.system_config import SystemConfigService

    monkeypatch.setenv("DATABASE_URL", server_db_url)
    alembic.command.upgrade(_cfg(tmp_path), "head")

    engine = sa.create_engine(server_db_url)
    try:
        cols = _columns(engine, "SystemConfig")
        assert str(cols["key"]["type"]) == "VARCHAR(255)" and str(cols["value"]["type"]).startswith("TEXT")
        with Session(engine) as session:
            svc = SystemConfigService(session)
            svc.set("k", "one")
            svc.set("k", "two")
            svc.set("tricky", "x\\' OR 1=1 --")
            svc.set("unicode", "한글 ünï")
            session.commit()
        with Session(engine) as session:
            svc = SystemConfigService(session)
            assert svc.get("k") == "two"
            assert svc.get("tricky") == "x\\' OR 1=1 --"
            assert svc.get("unicode") == "한글 ünï"
            count = session.execute(sa.select(sa.func.count()).select_from(SystemConfig)).scalar()
            assert count == 3
    finally:
        engine.dispose()
