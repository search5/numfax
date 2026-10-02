"""The session cookie's Secure flag comes from session.secure (ini) or NAMIFAX_SESSION_SECURE; the ini wins."""

from __future__ import annotations

import pytest
from pyramid.testing import DummyRequest

from namifax import _session_factory


def _secure(settings):
    return _session_factory({"session.secret": "x", **settings})(DummyRequest())._cookie_secure


def test_it_is_off_by_default(monkeypatch):
    monkeypatch.delenv("NAMIFAX_SESSION_SECURE", raising=False)
    assert _secure({}) is False


@pytest.mark.parametrize("value", ["1", "true", "YES"])
def test_the_environment_variable_turns_it_on(monkeypatch, value):
    monkeypatch.setenv("NAMIFAX_SESSION_SECURE", value)
    assert _secure({}) is True


def test_the_ini_wins_over_the_environment(monkeypatch):
    monkeypatch.setenv("NAMIFAX_SESSION_SECURE", "true")
    assert _secure({"session.secure": "false"}) is False
    monkeypatch.setenv("NAMIFAX_SESSION_SECURE", "false")
    assert _secure({"session.secure": "true"}) is True
