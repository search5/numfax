"""Spec 48 loop C5: serve_main ensures the schema through ensure_schema() and reports Pyramid startup failures."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import importlib

main_mod = importlib.import_module("namifax.main")  # `namifax.main` is also a function name in the package


def _serve(monkeypatch, make_app):
    monkeypatch.setenv("NAMIFAX_ENABLE_SCHEDULER", "0")
    calls = []

    def fake_ensure_schema(engine):
        calls.append(1)

    server = MagicMock()
    server.__enter__.return_value.serve_forever.side_effect = KeyboardInterrupt
    with patch.object(main_mod, "ensure_schema", fake_ensure_schema), \
            patch.object(main_mod, "make_server", return_value=server) as ms, \
            patch("namifax.create_app", make_app):
        code = main_mod.serve_main(["--port", "0"])
    return code, calls, ms


def test_serve_ensures_the_schema_without_a_global_engine(monkeypatch):
    pyramid_app = object()
    code, calls, ms = _serve(monkeypatch, MagicMock(return_value=pyramid_app))
    assert code == 0 and calls == [1]
    assert ms.call_args.args[2] is pyramid_app
