"""Spec 48 loop C5: serve_main ensures the schema through cli_db() and reports Pyramid startup failures."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import namifax.db.engine as engine_mod
import importlib

main_mod = importlib.import_module("namifax.main")  # `namifax.main` is also a function name in the package


def _serve(monkeypatch, make_app):
    monkeypatch.setenv("NAMIFAX_ENABLE_SCHEDULER", "0")
    monkeypatch.setattr(engine_mod, "_DEFAULT_ENGINE", None)
    calls = []

    @contextmanager
    def fake_cli_db(*a, **k):
        calls.append(1)
        yield object()

    server = MagicMock()
    server.__enter__.return_value.serve_forever.side_effect = KeyboardInterrupt
    fallback = MagicMock(name="fallback_app")
    with patch.object(main_mod, "cli_db", fake_cli_db), \
            patch.object(main_mod, "make_server", return_value=server) as ms, \
            patch.object(main_mod, "create_app", return_value=fallback), \
            patch("namifax.create_app", make_app):
        code = main_mod.serve_main(["--port", "0"])
    return code, calls, ms, fallback


def test_serve_ensures_schema_via_cli_db_without_global_engine(monkeypatch):
    pyramid_app = object()
    code, calls, ms, _ = _serve(monkeypatch, MagicMock(return_value=pyramid_app))
    assert code == 0 and calls == [1]
    assert ms.call_args.args[2] is pyramid_app
    assert engine_mod._DEFAULT_ENGINE is None


def test_pyramid_startup_failure_is_reported_before_falling_back(monkeypatch, capsys):
    code, _, ms, fallback = _serve(monkeypatch, MagicMock(side_effect=RuntimeError("db is down")))
    assert code == 0
    assert ms.call_args.args[2] is fallback
    err = capsys.readouterr().err
    assert "db is down" in err and "falling back" in err.lower()
