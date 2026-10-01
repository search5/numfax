"""Create or update the schema when the application (or a command) starts.

* SQLite: tables left by older versions of the port are first brought to the current layout
  (``sqlite_upgrade``), then the Alembic revisions create whatever is missing. Demo accounts and sample data are
  created only when asked for (``NAMIFAX_DEMO_DATA=1`` or ``demo.data = true``), and only in a brand-new SQLite
  database (development and the test suites).
* MySQL, MariaDB and PostgreSQL: the Alembic revisions (``upgrade head``) and only the default fax categories and
  cover pages. No demo accounts are created there: a database that serves real users must not start with a
  well-known password. The first administrator is made with ``namifax createuser``.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Mapping, Optional

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

_TRUE = ("1", "true", "yes", "on")


def demo_data_wanted(dialect: str, settings: Optional[Mapping[str, Any]] = None,
                     environ: Optional[Mapping[str, str]] = None) -> bool:
    """Is the demo data switched on, and is this a database that may have it (SQLite only)?"""
    environ = os.environ if environ is None else environ
    asked = str(environ.get("NAMIFAX_DEMO_DATA") or (settings or {}).get("demo.data") or "").strip().lower() in _TRUE
    if asked and dialect != "sqlite":
        logging.getLogger("namifax").warning("NAMIFAX_DEMO_DATA is ignored: demo data is only created in SQLite databases")
        return False
    return asked


def ensure_schema(engine: Engine, settings: Optional[Mapping[str, Any]] = None) -> None:
    """Bring the database behind ``engine`` up to date; safe to call on every start."""
    try:
        import sqlalchemy as sa

        # a database is new when it has none of the application's tables; only then does it get default records
        # (an installation that already has data keeps exactly what it has)
        fresh = "UserAccount" not in sa.inspect(engine).get_table_names()
        if engine.dialect.name == "sqlite":
            from namifax.db.sqlite_upgrade import upgrade_existing_sqlite

            with engine.begin() as connection:
                upgrade_existing_sqlite(connection)
        from namifax.db.adopt import adopt_existing_tables

        adopt_existing_tables(engine)
        upgrade_to_head(engine)
        with Session(engine) as session:
            from namifax.db import seed

            if demo_data_wanted(engine.dialect.name, settings):
                seed.seed_if_empty(session)
            elif fresh:
                seed.seed_default_records(session)
            session.commit()
    except Exception as exc:
        raise RuntimeError(f"Database initialisation failed: {exc}") from exc


def upgrade_to_head(engine: Engine) -> None:
    """Run the Alembic revisions on ``engine`` without needing an ini file."""
    import alembic.command
    from alembic.config import Config

    cfg = Config()
    cfg.set_main_option("script_location", "namifax:alembic")
    with engine.begin() as connection:
        cfg.attributes["connection"] = connection
        alembic.command.upgrade(cfg, "head")


def seed_default_records(session: Session) -> None:
    """Kept for callers that only want the default records."""
    from namifax.db import seed

    seed.seed_default_records(session)
