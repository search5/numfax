"""P3: a freshly created database is fully seeded on the very first initialisation."""

from __future__ import annotations

from namifax.db.engine import DatabaseEngine
from namifax.db.schema import init_database_tables


def test_first_init_links_seed_fax_to_company_without_second_init():
    db = DatabaseEngine()
    assert db.connect_sqlite(":memory:")
    assert init_database_tables(db)
    db.query("SELECT company FROM FaxArchive WHERE fid = 1")
    assert db.get_records()[0]["company"] == "Acme Corp"


def test_second_init_is_idempotent():
    db = DatabaseEngine()
    assert db.connect_sqlite(":memory:")
    init_database_tables(db)
    db.query("SELECT COUNT(*) AS n FROM FaxArchive")
    first = db.get_records()[0]["n"]
    init_database_tables(db)
    db.query("SELECT COUNT(*) AS n FROM FaxArchive")
    assert db.get_records()[0]["n"] == first
