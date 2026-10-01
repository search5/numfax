"""P5 (F): there is no process-wide default engine; domain objects need an injected database."""

from __future__ import annotations

import pytest

import namifax.db.engine as engine_mod
from namifax.db.engine import DatabaseEngine, MissingDatabase
from namifax.db.repository import MDBOData, Repository
from namifax.db.schema import init_database_tables
from namifax.services.addressbook import AFAddressBook
from namifax.services.archive_in import ArchiveIn
from namifax.services.did import DIDRouting
from namifax.services.user_account import AFUserAccount


@pytest.mark.parametrize("name", ["get_default_engine", "set_default_engine", "_DEFAULT_ENGINE"])
def test_global_default_engine_api_is_gone(name):
    assert not hasattr(engine_mod, name)


@pytest.fixture
def db():
    engine = DatabaseEngine()
    assert engine.connect_sqlite(":memory:")
    init_database_tables(engine)
    return engine


def test_repository_uses_injected_db(db):
    repo = Repository("DynConf", db=db)
    assert repo._db is db
    assert repo.data.get_db() is db


@pytest.mark.parametrize("factory", [Repository, MDBOData], ids=["Repository", "MDBOData"])
def test_repository_without_db_is_a_loud_placeholder(factory):
    repo = factory("UserAccount")
    assert isinstance(repo._db, MissingDatabase)
    with pytest.raises(RuntimeError, match="database"):
        repo.load(1)


@pytest.mark.parametrize("factory", [AFUserAccount, AFAddressBook, DIDRouting, ArchiveIn], ids=lambda f: f.__name__)
def test_domain_class_without_db_does_not_silently_use_another_database(factory):
    obj = factory()
    with pytest.raises(RuntimeError, match="database"):
        # every domain class reaches the database through its repository on first load
        for attr in ("load", "load_fax", "load_route", "loadbycid"):
            if hasattr(obj, attr):
                getattr(obj, attr)(1)
                break


def test_domain_class_with_db_reads_from_that_db(db):
    user = AFUserAccount(db=db)
    assert user.load(1) is True
