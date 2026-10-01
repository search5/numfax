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
