"""Limit repeated failed password sign-ins.

Failures are counted per user name (whether or not the account exists, so the answer never reveals which names are
real) and per client address (with a higher limit, since an address can be a whole office or a proxy). The counters live
in ``SystemConfig`` so every worker process sees the same state. After ``NAMIFAX_LOGIN_MAX_FAILURES`` (default 10)
failures within the lock period the password is not even checked until ``NAMIFAX_LOGIN_LOCK_MINUTES`` (default 15)
have passed. A successful sign-in clears the user-name counter (never the address one, or one's own account could be
used to reset it).
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any

IP_FACTOR = 5                                 # an address may fail this many times more than a single user name


def _now() -> float:                          # a seam for tests
    return time.time()


def _int_env(name: str, default: int) -> int:
    try:
        value = int(os.environ.get(name, "") or default)
    except ValueError:
        return default
    return value if value > 0 else default


def max_failures() -> int:
    return _int_env("NAMIFAX_LOGIN_MAX_FAILURES", 10)


def lock_seconds() -> int:
    return _int_env("NAMIFAX_LOGIN_LOCK_MINUTES", 15) * 60


def _key(kind: str, value: str) -> str:
    return f"login_throttle:{kind}:" + hashlib.sha256((value or "").strip().lower().encode()).hexdigest()[:32]


class LoginThrottle:
    def __init__(self, session: Any) -> None:
        from namifax.services.system_config import SystemConfigService

        self.cfg = SystemConfigService(session)

    @staticmethod
    def _parse(raw: str) -> dict[str, float]:
        try:
            state = json.loads(raw or "{}")
            return state if isinstance(state, dict) else {}
        except ValueError:
            return {}

    def _load(self, key: str) -> dict[str, float]:
        return self._parse(self.cfg.get(key, ""))

    def _keys(self, username: str, ip: str | None) -> list[tuple[str, int]]:
        keys = [(_key("user", username), max_failures())]
        if ip:
            keys.append((_key("ip", ip), max_failures() * IP_FACTOR))
        return keys

    def is_locked(self, username: str, ip: str | None = None) -> bool:
        now = _now()
        return any(float(self._load(key).get("until") or 0) > now for key, _limit in self._keys(username, ip))

    @staticmethod
    def _counted(state: dict, now: float, period: float, limit: int) -> dict:
        """The state after one more failure: a new window when the old one is over, and a lock when the limit is reached."""
        if not state.get("start") or now - float(state["start"]) > period:
            state = {"n": 0, "start": now}                             # an old window (or an expired lock): start again
        state["n"] = int(state.get("n", 0)) + 1
        if state["n"] >= limit:
            state["until"] = now + period
        return state

    def begin_attempt(self, username: str, ip: str | None = None) -> bool:
        """Count a sign-in attempt before its password is looked at; False (nothing counted) when the user name or the address is
        locked, so that the password is not looked at.

        The rows of the user name and the address are locked (``SystemConfigService.lock``), the user name always first, so
        attempts that arrive together are counted one after the other: of forty at once only as many as the limit are let
        through (the old order, ask whether it is locked, check the password, record the failure, let all forty be checked).
        The attempt that reaches the limit is allowed, and it locks at once. A success gives the address its count back
        (``record_success``)."""
        now, period = _now(), lock_seconds()
        rows = [(self.cfg.lock(key), limit) for key, limit in self._keys(username, ip)]
        states = [self._parse(row.value or "") for row, _ in rows]
        if any(float(state.get("until") or 0) > now for state in states):
            return False
        for (row, limit), state in zip(rows, states):
            row.value = json.dumps(self._counted(state, now, period, limit))
        self.cfg.session.flush()
        return True

    def record_failure(self, username: str, ip: str | None = None) -> None:
        """Count one failure after the fact (the sign-in view counts with ``begin_attempt`` before the password is checked).
        The counter is changed under a row lock (``locked_update``), so failures that arrive at the same moment are all counted
        and none of them ends in an error; the user name is always locked before the address."""
        now, period = _now(), lock_seconds()
        for key, limit in self._keys(username, ip):
            def count(raw: str, limit: int = limit) -> str:
                state = self._parse(raw)
                if float(state.get("until") or 0) > now:
                    return raw                                         # already locked: the clock is not extended
                return json.dumps(self._counted(state, now, period, limit))

            self.cfg.locked_update(key, count)

    def record_success(self, username: str, ip: str | None = None) -> None:
        """A right password clears the user name. With ``ip`` (the attempt was counted by ``begin_attempt``) the address gets that
        one count back, and the lock that this attempt itself caused, so that the successful sign-ins of an office never lock
        the address; the address is not cleared (one's own account could be used to reset it)."""
        key = _key("user", username)
        if self._load(key):
            self.cfg.locked_update(key, lambda raw: "{}")
        if ip:
            ip_key, limit = _key("ip", ip), max_failures() * IP_FACTOR

            def give_back(raw: str) -> str:
                state = self._parse(raw)
                state["n"] = max(int(state.get("n", 0)) - 1, 0)
                if state["n"] < limit:
                    state.pop("until", None)
                return json.dumps(state)

            if self._load(ip_key):
                self.cfg.locked_update(ip_key, give_back)
