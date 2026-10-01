"""The archive search and inbox follow the original AvantFAX query for every kind of account.

The expected lists were recorded by running the original ``FaxPDFArchive::search_archive`` / ``list_inbox`` (PHP 5.6 + MDB2
on MariaDB) over this same data: nine faxes and users with a modem only, a category only, both, neither, and a superuser.
Notable original behaviour: an empty modem or category list is not "no restriction" but a condition nothing matches, so an
account with neither sees only the faxes it sent itself.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select, text

from namifax.models import FaxArchive
from namifax.services.archive_base import FaxPDFArchive
from namifax.services.archive_in import ArchiveIn
from namifax.services.fax_access import FaxAccess
from namifax.services.user_account import AFUserAccount

# fid: (inbox, modemdev, faxcatid, sent_by)
FAXES = {
    1: (0, "ttyS0", None, None), 2: (0, "ttyS1", None, None), 3: (0, "ttyS0", 2, None), 4: (0, None, None, "alice"),
    5: (1, "ttyS0", None, None), 6: (1, "ttyS1", None, None), 7: (1, "ttyS0", 2, None), 8: (0, None, None, "carl"),
    9: (0, "ttyS1", 2, None),
}
# username: (modemdevs, faxcats, superuser)
USERS = {"alice": ("ttyS0", "1", 0), "bob": ("ttyS1", None, 0), "carl": (None, None, 0), "dan": ("ttyS0", None, 0),
         "root": (None, None, 1), "erin": (None, "2", 0), "fay": ("ttyS0", "2", 0)}

# recorded from the original: (user, sentrecvd) -> fids, newest first
ARCHIVE = {
    ("alice", "*"): [4, 3, 1], ("alice", "r"): [3, 1], ("alice", "s"): [4], ("alice", ""): [4, 3, 1],
    ("bob", "*"): [9, 2], ("bob", "r"): [9, 2], ("bob", "s"): [], ("bob", ""): [9, 2],
    ("carl", "*"): [8], ("carl", "r"): [], ("carl", "s"): [8], ("carl", ""): [8],
    ("dan", "*"): [3, 1], ("dan", "r"): [3, 1], ("dan", "s"): [], ("dan", ""): [3, 1],
    ("root", "*"): [9, 8, 4, 3, 2, 1], ("root", "r"): [9, 3, 2, 1], ("root", "s"): [8, 4], ("root", ""): [9, 8, 4, 3, 2, 1],
    ("erin", "*"): [9, 3], ("erin", "r"): [9, 3], ("erin", "s"): [], ("erin", ""): [],
    ("fay", "*"): [9, 3, 1], ("fay", "r"): [9, 3, 1], ("fay", "s"): [], ("fay", ""): [3, 1],
}
INBOX = {"alice": [5], "bob": [6], "carl": [], "dan": [5], "erin": [], "fay": [7, 5]}       # root: every modem, none configured


class _Request:
    def __init__(self, session, username):
        self.dbsession = session
        self.identity = {"username": username}


@pytest.fixture
def world(dbsession):
    dbsession.execute(FaxArchive.__table__.delete())
    uids = {}
    for name, (modems, cats, superuser) in USERS.items():
        svc = AFUserAccount(db=dbsession)
        assert svc.create({"username": name, "password": "Secret123!", "email": f"{name}@x.test", "name": name,
                           "last_login": "2026-01-01 10:00:00", "acc_enabled": 1, "modemdevs": modems, "faxcats": cats,
                           "superuser": superuser}), svc.error
        uids[name] = svc.get_uid()
    for fid, (inbox, modem, cat, sender) in FAXES.items():
        dbsession.add(FaxArchive(fid=fid, faxpath=f"/f/{fid}", pages=1, inbox=inbox, archstamp="2026-03-01 10:00:00",
                                 modemdev=modem, faxcatid=cat, userid=uids[sender] if sender else 0))
    dbsession.flush()
    return dbsession


def _search(session, user, sentrecvd):
    access = FaxAccess.for_request(_Request(session, user))
    criteria = {"sentrecvd": sentrecvd, "userid": None if access.superuser else access.uid, **access.search_rights()}
    archive = FaxPDFArchive(db=session)
    archive.search_archive(criteria)
    found = []
    while (fid := archive.next_archive_entry()):
        found.append(fid)
    return found


@pytest.mark.parametrize("user,sentrecvd", sorted(ARCHIVE), ids=[f"{u}-{s or 'default'}" for u, s in sorted(ARCHIVE)])
def test_archive_search_matches_the_original(world, user, sentrecvd):
    assert _search(world, user, sentrecvd) == ARCHIVE[(user, sentrecvd)]


@pytest.mark.parametrize("user", sorted(INBOX))
def test_inbox_matches_the_original(world, user):
    access = FaxAccess.for_request(_Request(world, user))
    inbox = ArchiveIn(db=world)
    rows = inbox.list_inbox(devices=access.devices, faxcats=access.categories, enable_did_routing=access.did_routing)
    assert [r["fid"] for r in rows] == INBOX[user]
    assert inbox.get_num_faxes(access.devices, access.categories, access.did_routing) == len(INBOX[user])


def test_a_superuser_sees_every_inbox_fax(world):
    access = FaxAccess.for_request(_Request(world, "root"))
    rows = ArchiveIn(db=world).list_inbox(devices=access.devices, faxcats=access.categories)
    assert [r["fid"] for r in rows] == [7, 6, 5]


# --- DID routing switched on (ENABLE_DID_ROUTING) -------------------------------------------------------------------------------
# Recorded from the original with $ENABLE_DID_ROUTING = true. The accounts have no modem at all, only DID routes, so a port
# that kept filtering by modem would show nobody anything. The fax modems and routes deliberately disagree (fax 3 came in
# on ttyS1 but route 1).

# fid: (inbox, modemdev, didr_id, faxcatid, sent_by)
DID_FAXES = {
    1: (0, "ttyS0", 1, None, None), 2: (0, "ttyS0", 2, None, None), 3: (0, "ttyS1", 1, 2, None), 4: (0, None, None, None, "alice"),
    5: (1, "ttyS0", 1, None, None), 6: (1, "ttyS0", 2, None, None), 7: (1, "ttyS1", 1, 2, None), 8: (0, None, None, None, "carl"),
    9: (0, "ttyS1", 2, 2, None),
}
# username: (didrouting, faxcats, superuser)
DID_USERS = {"alice": ("1", "1", 0), "bob": ("2", None, 0), "carl": (None, None, 0), "dan": ("1", None, 0),
             "root": (None, None, 1), "erin": (None, "2", 0), "fay": ("1", "2", 0)}
DID_INBOX = {"alice": [5], "bob": [6], "carl": [], "dan": [5], "erin": [], "fay": [7, 5], "root": [7, 6, 5]}   # root: the configured routes


@pytest.fixture
def did_world(dbsession, monkeypatch):
    monkeypatch.setenv("ENABLE_DID_ROUTING", "1")
    dbsession.execute(FaxArchive.__table__.delete())
    uids = {}
    for name, (routes, cats, superuser) in DID_USERS.items():
        svc = AFUserAccount(db=dbsession)
        assert svc.create({"username": name, "password": "Secret123!", "email": f"{name}@x.test", "name": name,
                           "last_login": "2026-01-01 10:00:00", "acc_enabled": 1, "didrouting": routes, "faxcats": cats,
                           "superuser": superuser}), svc.error
        uids[name] = svc.get_uid()
    for fid, (inbox, modem, route, cat, sender) in DID_FAXES.items():
        dbsession.add(FaxArchive(fid=fid, faxpath=f"/f/{fid}", pages=1, inbox=inbox, archstamp="2026-03-01 10:00:00",
                                 modemdev=modem, didr_id=route, faxcatid=cat, userid=uids[sender] if sender else 0))
    dbsession.flush()
    return dbsession


@pytest.mark.parametrize("user,sentrecvd", sorted(ARCHIVE), ids=[f"{u}-{s or 'default'}" for u, s in sorted(ARCHIVE)])
def test_archive_search_with_did_routing_matches_the_original(did_world, user, sentrecvd):
    assert _search(did_world, user, sentrecvd) == ARCHIVE[(user, sentrecvd)]      # the same lists as with modems


@pytest.mark.parametrize("user", sorted(DID_INBOX))
def test_inbox_with_did_routing_matches_the_original(did_world, user):
    access = FaxAccess.for_request(_Request(did_world, user))
    inbox = ArchiveIn(db=did_world)
    rows = inbox.list_inbox(devices=access.devices, faxcats=access.categories, enable_did_routing=access.did_routing)
    assert [r["fid"] for r in rows] == DID_INBOX[user]
