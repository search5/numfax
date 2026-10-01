"""Create or update the schema when the application (or a command) starts.

* SQLite: tables left by older versions of the port are first brought to the current layout
  (``sqlite_upgrade``), then the Alembic revisions create whatever is missing. A brand-new SQLite database also
  gets the demo data (development and the test suites).
* MySQL, MariaDB and PostgreSQL: the Alembic revisions (``upgrade head``) and only the default fax categories and
  cover pages. No demo accounts are created there: a database that serves real users must not start with a
  well-known password. The first administrator is made with ``namifax createuser``.
"""

from __future__ import annotations

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session


def ensure_schema(engine: Engine) -> None:
    """Bring the database behind ``engine`` up to date; safe to call on every start."""
    try:
        if engine.dialect.name == "sqlite":
            from namifax.db.sqlite_upgrade import upgrade_existing_sqlite

            with engine.begin() as connection:
                upgrade_existing_sqlite(connection)
        upgrade_to_head(engine)
        with Session(engine) as session:
            from namifax.db import seed

            if engine.dialect.name == "sqlite":
                seed.seed_if_empty(session)
            else:
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
