"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from namifax.db.engine import DatabaseEngine
from namifax.db.schema import init_database_tables


@pytest.fixture
def seeded_db():
    """Isolated in-memory DatabaseEngine with schema and seed data (no global DB)."""
    engine = DatabaseEngine()
    assert engine.connect_sqlite(":memory:")
    init_database_tables(engine)
    yield engine
    engine.disconnect()


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    """Point the application at a per-test database so no test touches the working-tree namifax.db."""
    import namifax.db.engine as engine_mod

    db_file = tmp_path / "namifax-test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("NAMIFAX_DB_PATH", str(db_file))
    monkeypatch.delenv("AFDB_URL", raising=False)
    monkeypatch.setattr(engine_mod, "_DEFAULT_ENGINE", None)
    yield
    default = engine_mod._DEFAULT_ENGINE
    if default is not None:
        default.disconnect()
