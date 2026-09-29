"""NamiFAX SQLAlchemy Models and Pyramid Session Factory Integration."""

from __future__ import annotations

import os
from sqlalchemy import create_engine, engine_from_config
from sqlalchemy.orm import configure_mappers, sessionmaker

from namifax.models.meta import Base

# Ensure all entities are registered to Base
from namifax.models import entities  # noqa: F401

configure_mappers()


def get_engine(settings=None, prefix="sqlalchemy."):
    """Create SQLAlchemy engine from settings or environment."""
    if settings and any(k.startswith(prefix) for k in settings):
        return engine_from_config(settings, prefix)

    db_url = os.environ.get(
        "DATABASE_URL",
        os.environ.get("AFDB_URL", "sqlite:///:memory:"),
    )
    return create_engine(db_url)


def get_session_factory(engine):
    """Create session factory bound to engine."""
    return sessionmaker(bind=engine, expire_on_commit=False)


def includeme(config):
    """Pyramid extension hook: config.include('namifax.models')."""
    settings = config.get_settings()
    engine = settings.get("dbengine")
    if not engine:
        engine = get_engine(settings)

    session_factory = get_session_factory(engine)
    config.registry["dbsession_factory"] = session_factory

    # Try integrating pyramid_tm if installed
    try:
        import zope.sqlalchemy
        config.include("pyramid_tm")
        settings["tm.manager_hook"] = "pyramid_tm.explicit_manager"

        def dbsession(request):
            session = session_factory(info={"request": request})
            zope.sqlalchemy.register(session, transaction_manager=request.tm)
            return session
    except ImportError:
        def dbsession(request):
            session = session_factory(info={"request": request})
            request.add_finished_callback(lambda req: session.close())
            return session

    config.add_request_method(dbsession, reify=True)
