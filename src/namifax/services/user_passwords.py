from __future__ import annotations

from typing import Any

from namifax.auth.password import PasswordManager
from namifax.db.engine import DatabaseEngine
from namifax.db.repository import MDBOData


class AFUserPasswords:
    """Service class for managing user password history (UserPasswords table)."""

    def __init__(
        self,
        db: DatabaseEngine | None = None,
        engine: DatabaseEngine | None = None,
        repo: MDBOData | None = None,
    ) -> None:
        self.db = db or engine
        if repo is not None:
            self.userpasswords = repo
        else:
            self.userpasswords = MDBOData("UserPasswords", db=self.db)

        self.upid: int | None = None
        self.uid: int | None = None
        self.pwdhash: str | None = None

    def log_password(self, pwd: str, uid: int) -> bool:
        """Hash and record password in UserPasswords history table."""
        if not pwd or uid is None:
            return False

        pwdhash = PasswordManager.hash_password(pwd)
        return bool(self.userpasswords.new_entry({"uid": uid, "pwdhash": pwdhash}))

    def password_used(self, pwd: str, uid: int) -> bool:
        """Check if password hash already exists in history for user."""
        if not pwd or uid is None:
            return False

        pwdhash = PasswordManager.hash_password(pwd)
        res = self.userpasswords.find({"uid": uid, "pwdhash": pwdhash})
        return bool(res)

    def clear_hashes(self, uid: int) -> bool:
        """Clear all historical password records for user."""
        if uid is None:
            return False

        if self.db:
            res = self.db.query("DELETE FROM UserPasswords WHERE uid = :uid", params={"uid": uid})
            return bool(res.executed)

        # Fallback to repository raw query
        return bool(self.userpasswords.query(f"DELETE FROM UserPasswords WHERE uid = {int(uid)}"))


# Modern architectural alias
PasswordHistoryService = AFUserPasswords
