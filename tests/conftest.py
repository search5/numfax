"""Shared pytest fixtures."""

from __future__ import annotations

import os

import pytest
import transaction
import webtest
from pyramid.scripting import prepare
from pyramid.testing import DummyRequest, testConfig

from namifax import create_app, models
from namifax.db.engine import DatabaseEngine
from namifax.db.provider import create_sa_engine, resolve_database_url
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
    db_file = tmp_path / "namifax-test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("NAMIFAX_DB_PATH", str(db_file))
    monkeypatch.delenv("AFDB_URL", raising=False)
    yield


# --- Pyramid starter style fixtures -------------------------------------------------------
# A doomed transaction manager and a session joined to it make every database write made through
# ``request.dbsession`` disappear at the end of the test, without touching other tests.

@pytest.fixture
def dbengine():
    """SQLAlchemy engine for this test's isolated database."""
    engine = create_sa_engine(resolve_database_url({}, os.environ))
    yield engine
    engine.dispose()


@pytest.fixture
def app(dbengine):
    """The WSGI application bound to the isolated database engine."""
    return create_app(dbengine=dbengine)


@pytest.fixture
def tm():
    tm = transaction.TransactionManager(explicit=True)
    tm.begin()
    tm.doom()

    yield tm

    tm.abort()


@pytest.fixture
def dbsession(app, tm):
    session_factory = app.registry["dbsession_factory"]
    session = models.get_tm_session(session_factory, tm)
    yield session
    session.close()


@pytest.fixture
def testapp(app, tm, dbsession):
    """WebTest client whose requests share the externally controlled session and manager."""
    return webtest.TestApp(app, extra_environ={
        "HTTP_HOST": "example.com",
        "tm.active": True,
        "tm.manager": tm,
        "app.dbsession": dbsession,
    })


@pytest.fixture
def app_request(app, tm, dbsession):
    """A real request (extensions applied) joined to the fixture session and manager."""
    with prepare(registry=app.registry) as env:
        request = env["request"]
        request.host = "example.com"
        # without this, request.dbsession would use a different Session in a separate transaction
        request.dbsession = dbsession
        request.tm = tm
        yield request


@pytest.fixture
def dummy_request(tm, dbsession):
    """A lightweight dummy request: no request extensions, no threadlocals."""
    request = DummyRequest()
    request.host = "example.com"
    request.dbsession = dbsession
    request.tm = tm
    return request


@pytest.fixture
def dummy_config(dummy_request):
    """A dummy Configurator for ``dummy_request``, with the threadlocals pushed."""
    with testConfig(request=dummy_request) as config:
        yield config
