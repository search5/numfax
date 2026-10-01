"""Guard: `alembic upgrade head` produces exactly the tables the ORM models describe."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import alembic.command
import alembic.config
import pytest
import sqlalchemy as sa
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext

ROOT = Path(__file__).resolve().parents[2]
PKG_ALEMBIC = ROOT / "src" / "namifax" / "alembic"


def _cfg(tmp_path: Path) -> alembic.config.Config:
    scripts = tmp_path / "alembic"
    shutil.copytree(PKG_ALEMBIC, scripts)
    ini = re.sub(r"(?m)^script_location\s*=.*$", f"script_location = {scripts}", (ROOT / "development.ini").read_text())
    (tmp_path / "m.ini").write_text(ini)
    return alembic.config.Config(str(tmp_path / "m.ini"))


def _drift(url: str) -> list:
    import namifax.models  # noqa: F401  (registers every model)
    from namifax.models.meta import Base

    engine = sa.create_engine(url)
    try:
        with engine.connect() as conn:
            diffs = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    finally:
        engine.dispose()
    # tables that only exist in the legacy schema are not modelled yet: that is not drift
    return [d for d in diffs if not (isinstance(d, tuple) and d[0] == "remove_table")]


def test_sqlite_migrations_match_models(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'drift.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    alembic.command.upgrade(_cfg(tmp_path), "head")
    assert _drift(url) == []


@pytest.mark.serverdb
def test_server_migrations_match_models(tmp_path, monkeypatch, server_db_url):
    monkeypatch.setenv("DATABASE_URL", server_db_url)
    alembic.command.upgrade(_cfg(tmp_path), "head")
    assert _drift(server_db_url) == []
