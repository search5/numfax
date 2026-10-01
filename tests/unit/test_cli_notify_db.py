"""Spec 48 loop C2: notify CLI builds every domain object from one injected/opened database."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from namifax.cli import notify as mod

QFILE = (
    "totpages:2\nstatus:Normal\nexternal:12345678\njobid:999\nmailaddr:test@example.com\n"
    "owner:admin\ncompany:Acme Corp\nregarding:Docs\npostscript:0:0:/tmp/doc.ps\n"
)


def _run(tmp_path, **kwargs):
    qfile = tmp_path / "q1"
    qfile.write_text(QFILE)
    classes = {n: MagicMock(name=n) for n in ("AFAddressBook", "AFUserAccount", "ArchiveOut")}
    ab = classes["AFAddressBook"].return_value
    ab.loadbyfaxnum.return_value = False
    ab.create.return_value = True
    ab.create_faxnumid.return_value = True
    ab.get_companyid.return_value = 10
    ab.get_company.return_value = "Acme Corp"
    ab.get_description.return_value = ""
    user = classes["AFUserAccount"].return_value
    user.load_username.return_value = True
    user.email, user.language = "admin@example.com", "en"
    user.get_uid.return_value = 1
    classes["ArchiveOut"].return_value.create.return_value = True
    classes["ArchiveOut"].return_value.get_fid.return_value = 42
    with patch.multiple(mod, **classes), patch.object(mod, "send_mail"), \
            patch.object(mod, "convert2pdf", return_value=True), patch.object(mod, "pdf_preview"):
        code = mod.run_notify(["notify.py", str(qfile), "done", "00:01:23"], **kwargs)
    return code, classes


def test_injected_db_reaches_every_domain_object(tmp_path, monkeypatch):
    db = object()
    code, classes = _run(tmp_path, db=db)
    assert code == 0
    for name, cls in classes.items():
        assert cls.call_args_list, f"{name} not built"
        for call in cls.call_args_list:
            assert call.kwargs.get("db") is db, name


def test_without_injected_db_opens_cli_db_once(tmp_path):
    opened, calls = object(), []

    @contextmanager
    def fake_cli_db(*a, **k):
        calls.append(1)
        yield opened

    with patch.object(mod, "cli_db", fake_cli_db):
        code, classes = _run(tmp_path)
    assert code == 0 and calls == [1]
    assert classes["AFUserAccount"].call_args.kwargs.get("db") is opened


def test_usage_and_missing_qfile_do_not_open_a_database(tmp_path):
    with patch.object(mod, "cli_db", side_effect=AssertionError("must not open DB")):
        assert mod.run_notify(["notify.py"]) == 0
        assert mod.run_notify(["notify.py", str(tmp_path / "nope"), "done"]) == 0
