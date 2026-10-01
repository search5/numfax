"""Spec 48 loop C1: faxrcvd CLI builds every domain object from one injected/opened database."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import namifax.db.engine as engine_mod
from namifax.cli import faxrcvd as mod


def _run(tmp_path, **kwargs):
    tiff = tmp_path / "fax00123.tif"
    tiff.write_bytes(b"mock tiff")
    classes = {n: MagicMock(name=n) for n in ("FaxModem", "AFAddressBook", "ArchiveIn", "DIDRouting", "BarcodeRouting")}
    classes["ArchiveIn"].return_value.create.return_value = True
    classes["ArchiveIn"].return_value.get_fid.return_value = 7
    with patch.multiple(mod, **classes), \
            patch.object(mod, "faxinfo", return_value={"Sender": "1", "Pages": "1", "Received": "2026:10:01 10:00:00"}), \
            patch.object(mod, "tiff2pdf"), patch.object(mod, "static_preview"), patch.object(mod, "send_mail"), \
            patch.object(mod, "bardecode", return_value=None), \
            patch("namifax.services.ocr.OcrService") as ocr:
        code = mod.run_faxrcvd(["faxrcvd.py", str(tiff), "ttyS0", "comm01", "none"], **kwargs)
    return code, classes, ocr


def test_injected_db_reaches_every_domain_object(tmp_path, monkeypatch):
    monkeypatch.setattr(engine_mod, "_DEFAULT_ENGINE", None)
    db = object()
    code, classes, ocr = _run(tmp_path, db=db)
    assert code == 0
    for name in ("FaxModem", "AFAddressBook", "ArchiveIn", "DIDRouting"):
        assert classes[name].call_args_list, f"{name} not built"
        for call in classes[name].call_args_list:
            assert call.kwargs.get("db") is db, name
    assert ocr.call_args.kwargs.get("db") is db
    assert engine_mod._DEFAULT_ENGINE is None


def test_without_injected_db_opens_cli_db_once(tmp_path):
    opened = object()
    calls = []

    @contextmanager
    def fake_cli_db(*a, **k):
        calls.append(1)
        yield opened

    with patch.object(mod, "cli_db", fake_cli_db):
        code, classes, _ = _run(tmp_path)
    assert code == 0 and calls == [1]
    assert classes["FaxModem"].call_args.kwargs.get("db") is opened


def test_usage_does_not_open_a_database():
    with patch.object(mod, "cli_db", side_effect=AssertionError("must not open DB for usage")):
        assert mod.run_faxrcvd(["faxrcvd.py"]) == 0
