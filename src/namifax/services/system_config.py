"""Read and write SystemConfig key/value settings through an ORM session."""

from __future__ import annotations

from sqlalchemy.orm import Session

from namifax.models.systemconfig import SystemConfig


class SystemConfigService:
    """Key/value settings backed by the ``SystemConfig`` table.

    Uses ``Session.merge`` for writes, so the upsert is portable across SQLite, MySQL, MariaDB
    and PostgreSQL (no ``INSERT OR REPLACE``) and values are bound parameters, never string-built SQL.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, key: str, default: str = "") -> str:
        row = self.session.get(SystemConfig, key)
        if row is None or row.value is None:
            return default
        return row.value

    def get_secret(self, key: str, default: str = "") -> str:
        """A value stored with ``set_secret`` (or, from before encryption existed, in plain text)."""
        from namifax.common.secretbox import decrypt

        stored = self.get(key, "")
        return decrypt(stored) if stored else default

    def set_secret(self, key: str, value: str) -> None:
        """Store ``value`` encrypted; raises ``SecretKeyError`` when no encryption key is configured."""
        from namifax.common.secretbox import encrypt

        self.set(key, encrypt(value))

    def set(self, key: str, value: str) -> None:
        self.session.merge(SystemConfig(key=key, value=value))
        self.session.flush()
