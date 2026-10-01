"""A legacy ``DatabaseEngine`` and an ORM ``Session`` over ONE seeded in-memory database.

Several tests build data through the legacy engine and then drive code that now reads it through the
session (or the reverse). A static pool gives both the same connection, so each sees the other's writes.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from namifax.db.provider import create_sa_engine, open_db
from namifax.db.schema import init_database_tables


def linked_db():
    """Return ``(db, session)``; close the session, then the db, when done."""
    engine = create_sa_engine("sqlite://")
    db = open_db(engine)
    assert init_database_tables(db)
    return db, Session(engine)


def close_linked(db, session) -> None:
    session.close()
    db.disconnect()
