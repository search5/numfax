"""Create or update the schema when the application (or a command) starts.

* SQLite keeps the long-standing path: ``init_database_tables`` creates the legacy tables, migrates
  databases written by older versions of the port and, in a brand-new database, adds the demo data.
* MySQL, MariaDB and PostgreSQL get their tables from the Alembic revisions (``upgrade head``) and
  only the default fax categories and cover pages. No demo accounts are created there: a database
  that serves real users must not start with a well-known password. The first administrator is made
  with ``namifax createuser``.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session


def ensure_schema(engine: Engine) -> None:
    """Bring the database behind ``engine`` up to date; safe to call on every start."""
    if engine.dialect.name == "sqlite":
        _init_sqlite(engine)
        return
    upgrade_to_head(engine)
    with Session(engine) as session:
        seed_default_records(session)
        session.commit()


def _init_sqlite(engine: Engine) -> None:
    from namifax.db.provider import open_db
    from namifax.db.schema import init_database_tables

    boot = open_db(engine)
    try:
        if not init_database_tables(boot):
            raise RuntimeError(f"Database initialisation failed: {boot.get_error()}")
    finally:
        boot.disconnect()


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
    """Default fax categories and cover pages, only while their table is empty."""
    from namifax.models import CoverPages, FaxCategory

    if session.execute(select(func.count()).select_from(FaxCategory)).scalar_one() == 0:
        session.add_all([FaxCategory(name=n) for n in ("General", "Invoices", "Legal")])
    if session.execute(select(func.count()).select_from(CoverPages)).scalar_one() == 0:
        session.add_all([CoverPages(title="standard", file="standard.ps"), CoverPages(title="urgent", file="urgent.ps")])
    session.flush()
