"""Shared pytest fixtures."""

from __future__ import annotations

import re
import shutil
import os
import uuid
from pathlib import Path

import alembic.config
import pytest
import sqlalchemy as sa
import transaction
import webtest
from pyramid.request import Request
from pyramid.scripting import prepare
from pyramid.testing import DummyRequest, testConfig

from namifax import create_app, models
from namifax.db.provider import create_sa_engine, resolve_database_url
from sqlsession import seeded_session


@pytest.fixture
def seeded_db():
    """Isolated in-memory SqlSession (a real Session) with schema and seed data."""
    session = seeded_session()
    yield session
    session.disconnect()


@pytest.fixture(autouse=True)
def _demo_data(monkeypatch):
    """Most tests rely on the sample accounts and rows; the tests of the default (off) behaviour remove the switch."""
    monkeypatch.setenv("NAMIFAX_DEMO_DATA", "1")


@pytest.fixture(autouse=True)
def _secret_key(monkeypatch):
    """A fixed key so credentials can be stored in any test (tests of the missing-key case remove it)."""
    monkeypatch.setenv("NAMIFAX_SECRET_KEY", "test-only-passphrase-for-the-suite")


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


# --- real database servers (opt-in) --------------------------------------------------------
# Each test using ``server_db_url`` runs once per configured server on a throw-away database:
#   NAMIFAX_TEST_PG_URL      postgresql+psycopg://user:pw@host:port/postgres
#   NAMIFAX_TEST_MYSQL_URL   mysql+pymysql://user:pw@host:port/
#   NAMIFAX_TEST_MARIADB_URL mariadb+pymysql://user:pw@host:port/
SERVER_DB_ENV = {
    "postgresql": "NAMIFAX_TEST_PG_URL",
    "mysql": "NAMIFAX_TEST_MYSQL_URL",
    "mariadb": "NAMIFAX_TEST_MARIADB_URL",
}


@pytest.fixture(params=list(SERVER_DB_ENV), ids=list(SERVER_DB_ENV))
def server_db_url(request):
    """URL of a freshly created, empty database on a real server (skipped when not configured)."""
    env_name = SERVER_DB_ENV[request.param]
    base = os.environ.get(env_name)
    if not base:
        pytest.skip(f"{env_name} not set")
    name = f"nami_test_{uuid.uuid4().hex[:8]}"
    admin = sa.create_engine(base, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        if request.param == "postgresql":
            conn.execute(sa.text(f'CREATE DATABASE "{name}"'))
        else:
            conn.execute(sa.text(f"CREATE DATABASE `{name}` CHARACTER SET utf8mb4"))
    url = sa.engine.make_url(base).set(database=name).render_as_string(hide_password=False)
    yield url
    with admin.connect() as conn:
        if request.param == "postgresql":
            conn.execute(sa.text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        else:
            conn.execute(sa.text(f"DROP DATABASE IF EXISTS `{name}`"))
    admin.dispose()


# --- Alembic ------------------------------------------------------------------------------

@pytest.fixture
def alembic_cfg(tmp_path):
    """Alembic Config using a private copy of the migration environment.

    The target database is resolved as in the application: ``DATABASE_URL`` from the environment
    (tests set it with ``monkeypatch``) unless the ini file provides ``sqlalchemy.url``.
    """
    root = Path(__file__).resolve().parents[1]
    scripts = tmp_path / "alembic"
    shutil.copytree(root / "src" / "namifax" / "alembic", scripts)
    ini = re.sub(r"(?m)^script_location\s*=.*$", f"script_location = {scripts}", (root / "development.ini").read_text())
    ini_path = tmp_path / "alembic-test.ini"
    ini_path.write_text(ini)
    return alembic.config.Config(str(ini_path))


@pytest.fixture
def admin_call(app, tm, dbsession):
    """Call an admin view as a superadmin, with the fixture session and transaction manager."""
    def call(view, method="GET", params=None, path="/admin/x"):
        req = Request.blank(path, POST=params) if method == "POST" else Request.blank(path)
        with prepare(registry=app.registry, request=req) as env:
            request = env["request"]
            request.dbsession, request.tm = dbsession, tm
            request.session = {"is_superadmin": True, "is_admin": True, "username": "admin"}
            return view(request)
    return call


# --- a database created by the original AvantFAX (MySQL / MariaDB only) --------------------------------------
# Built from the original installer's SQL (legacy/create_tables.sql) plus its later update scripts, with a few
# rows written the way the original application wrote them. ``3.3.5`` is a current installation, ``3.2.0`` an old one.
LEGACY_ROOT = Path(__file__).resolve().parents[1] / "legacy"
LEGACY_VERSIONS = {"3.3.5": ["db-update-334.sql"], "3.2.0": []}


def _legacy_statements(path):
    sql = "\n".join(l for l in path.read_text().splitlines() if not l.strip().startswith("--"))
    return [part.strip() for part in sql.split(";") if part.strip()]


LEGACY_SAMPLE_ROWS = [
    "INSERT INTO UserAccount SET name='Old User', username='olduser', password='5f4dcc3b5aa765d61d8327deb882cf99', "
    "email='old@corp.test', acc_enabled=TRUE, last_login='2025-12-31 23:59:58', last_ip='10.1.2.3', pwdexpire='2027-01-31', "
    "pwdcycle=90, language='ko', modemdevs='ttyS0|ttyS1', faxperpageinbox=25",
    "INSERT INTO AddressBook SET company='Legacy Corp'",
    "INSERT INTO AddressBookFAX SET abook_id=2, faxnumber='5550001', description='main', to_person='Kim'{extra}",
    "INSERT INTO AddressBookEmail SET abook_id=2, contact_name='Kim', contact_email='kim@legacy.test'",
    "INSERT INTO FaxCategory SET name='Invoices'",
    "INSERT INTO Modems SET device='ttyS0', alias='Modem 1'",
    "INSERT INTO DistroList SET listname='Board', listdata='5550001', lastmod_date='2025-11-30 08:15:00', lastmod_user=1",
    "INSERT INTO SysLog SET logdate='2025-12-24 18:30:00', logtext='legacy log line'",
    "INSERT INTO FaxArchive SET faxnumid=1, faxpath='/faxes/2012/01/02/5550001/00007', pages=2, "
    "archstamp='2012-01-02 03:04:05', lastoperation='2012-01-02 03:04:05', modemdev='ttyS0', origfaxnum='5550001', inbox=1",
    "INSERT INTO FaxArchive SET faxnumid=1, faxpath='/faxes/2011/05/06/5550001/00003', pages=1, "
    "archstamp='2011-05-06 07:08:09', modemdev='ttyS0', origfaxnum='5550001', inbox=0, description='old fax'",
]


class LegacyDatabase:
    def __init__(self, url, engine, version):
        self.url, self.engine, self.version = url, engine, version


@pytest.fixture(params=[("mysql", "3.3.5"), ("mysql", "3.2.0"), ("mariadb", "3.3.5"), ("mariadb", "3.2.0")],
                ids=lambda p: f"{p[0]}-{p[1]}")
def legacy_db(request, monkeypatch):
    """A MySQL/MariaDB database as the original AvantFAX leaves it (skipped when the server is not configured)."""
    kind, version = request.param
    base = os.environ.get(SERVER_DB_ENV[kind])
    if not base:
        pytest.skip(f"{SERVER_DB_ENV[kind]} not set")
    name = f"nami_legacy_{uuid.uuid4().hex[:8]}"
    admin = sa.create_engine(base, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(sa.text(f"CREATE DATABASE `{name}` CHARACTER SET utf8mb4"))
    url = sa.engine.make_url(base).set(database=name).render_as_string(hide_password=False)
    engine = sa.create_engine(url)
    with engine.begin() as conn:
        for statement in _legacy_statements(LEGACY_ROOT / "create_tables.sql"):
            conn.execute(sa.text(statement))
        for script in LEGACY_VERSIONS[version]:
            for statement in _legacy_statements(LEGACY_ROOT / script):
                conn.execute(sa.text(statement))
        extra = ", to_address='', to_zip='', to_city=''" if version == "3.3.5" else ""   # NOT NULL since 3.3.4
        for statement in LEGACY_SAMPLE_ROWS:
            conn.execute(sa.text(statement.replace("{extra}", extra)))
    monkeypatch.setenv("DATABASE_URL", url)
    yield LegacyDatabase(url, engine, version)
    engine.dispose()
    with admin.connect() as conn:
        conn.execute(sa.text(f"DROP DATABASE IF EXISTS `{name}`"))
    admin.dispose()


@pytest.fixture
def as_superuser(monkeypatch):
    """Views check the signed-in user's fax rights in the database; this makes them see a superuser.

    For tests that call a view directly with a stand-in request (there is no login behind it). Like a real superuser the
    inbox is limited to the modems and DID routes that are set up (read from the request's session when it is a real one).
    """
    from namifax.services.did import DIDRouting
    from namifax.services.fax_access import FaxAccess
    from namifax.services.modem import FaxModem

    def superuser(cls, request):
        modems, routes = [], []
        try:
            modems = FaxModem(db=request.dbsession).get_modems() or []
            routes = DIDRouting(db=request.dbsession).get_routes() or []
        except Exception:
            pass                                               # a stand-in session with no database behind it
        return cls(uid=1, username="admin", superuser=True, can_del=True, configured_modems=modems, configured_routes=routes)

    monkeypatch.setattr(FaxAccess, "for_request", classmethod(superuser))
