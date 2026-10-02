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

    def record_failure(self, username: str, ip: str | None = None) -> None:
        """Count one failure. The counter is changed under a row lock (``locked_update``), so failures that arrive at the same
        moment are all counted and none of them ends in an error; the user name is always locked before the address, so two
        requests cannot wait for each other."""
        now, period = _now(), lock_seconds()
        for key, limit in self._keys(username, ip):
            def count(raw: str, limit: int = limit) -> str:
                state = self._parse(raw)
                if float(state.get("until") or 0) > now:
                    return raw                                         # already locked: the clock is not extended
                if not state.get("start") or now - float(state["start"]) > period:
                    state = {"n": 0, "start": now}                     # an old window (or an expired lock): start again
                state["n"] = int(state.get("n", 0)) + 1
                if state["n"] >= limit:
                    state["until"] = now + period
                return json.dumps(state)

            self.cfg.locked_update(key, count)

    def record_success(self, username: str) -> None:
        key = _key("user", username)
        if self._load(key):
            self.cfg.set(key, "{}")
