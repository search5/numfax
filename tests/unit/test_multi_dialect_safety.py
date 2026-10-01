"""Multi-database safety: fail fast on schema errors and escape literals per SQL dialect."""

from __future__ import annotations

import sqlite3
from unittest.mock import patch

import pytest

from namifax.db.engine import DatabaseEngine


# --- schema initialisation must not fail silently ------------------------------------

def test_create_app_fails_fast_when_schema_initialisation_fails(tmp_path):
    from namifax import create_app

    with patch("namifax.db.schema.init_database_tables", return_value=False):
        with pytest.raises(RuntimeError, match="initiali[sz]ation failed"):
            create_app(**{"sqlalchemy.url": f"sqlite:///{tmp_path / 'x.db'}"})


def test_cli_db_fails_fast_when_schema_initialisation_fails(tmp_path):
    from namifax.db.provider import cli_db

    with patch("namifax.db.schema.init_database_tables", return_value=False):
        with pytest.raises(RuntimeError, match="initiali[sz]ation failed"):
            with cli_db(environ={"DATABASE_URL": f"sqlite:///{tmp_path / 'y.db'}"}):
                pytest.fail("the block must not run")


# --- quote() escapes by dialect -------------------------------------------------------

PAYLOAD = "x\\' OR 1=1 -- "


def _engine(dialect):
    db = DatabaseEngine.from_connection(sqlite3.connect(":memory:"), dialect=dialect)
    return db


@pytest.mark.parametrize("dialect", ["mysql", "mariadb"])
def test_mysql_family_escapes_backslashes_before_quotes(dialect):
    # MySQL treats \' as an escaped quote, so an unescaped backslash would end the literal early.
    assert _engine(dialect).quote(PAYLOAD) == "'x\\\\'' OR 1=1 -- '"


@pytest.mark.parametrize("dialect", ["sqlite", "postgresql"])
def test_standard_dialects_only_double_single_quotes(dialect):
    assert _engine(dialect).quote(PAYLOAD) == "'x\\'' OR 1=1 -- '"


def test_quote_handles_none_and_defaults_to_standard_escaping():
    db = DatabaseEngine()
    assert db.quote(None) == "NULL"
    assert db.quote("a'b") == "'a''b'"
    assert db.dialect == "sqlite"


def test_connect_sqlite_and_open_db_report_their_dialect(tmp_path):
    from namifax.db.provider import create_sa_engine, open_db

    db = DatabaseEngine()
    assert db.connect_sqlite(":memory:") and db.dialect == "sqlite"
    opened = open_db(create_sa_engine(f"sqlite:///{tmp_path / 'z.db'}"))
    assert opened.dialect == "sqlite"
    opened.disconnect()
