import logging
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import pyotp
from namifax.common.secretbox import SecretDecryptError, SecretKeyError, decrypt, encrypt
from namifax.db.repository import Repository


# Brute-force protection: a 6-digit code has only a million values, so wrong codes are counted per user
# (in the database, so every worker sees the same count) and the account is locked for a while.
MAX_FAILED_ATTEMPTS = 5
LOCK_MINUTES = 15
_TS = "%Y-%m-%d %H:%M:%S"


class TotpService:
    """RFC 6238 Time-based One-Time Password (TOTP) two-factor authentication service."""

    def __init__(self, db: Any = None) -> None:
        from namifax.db.engine import resolve_db

        self.db = db if not hasattr(db, "execute") else db   # a Session is used as is
        if db is None:
            self.db = resolve_db(None, "TotpService")

    @staticmethod
    def generate_secret() -> str:
        """Generate a random Base32 secret."""
        return pyotp.random_base32()

    @staticmethod
    def get_provisioning_uri(username: str, secret: str, issuer: str = "NamiFAX") -> str:
        """Generate standard otpauth:// provisioning URI for Authenticator apps."""
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=username, issuer_name=issuer)

    @staticmethod
    def verify_code(secret: str, code: str) -> bool:
        """Verify 6-digit TOTP challenge token within valid time window."""
        if not secret or not code:
            return False
        totp = pyotp.TOTP(secret)
        return totp.verify(code.strip())

    def _rows(self, uid: int) -> Any:
        return Repository("UserTOTP", db=self.db)

    def is_totp_enabled(self, uid: int) -> bool:
        """Check whether 2FA is currently active for the given user ID."""
        row = self._rows(uid).find({"uid": int(uid)})
        if isinstance(row, list):
            row = row[0] if row else None
        return bool(row and _flag(row.get("is_enabled")))

    def enable_totp(self, uid: int, secret: str, code: str) -> Dict[str, Any]:
        """Validate challenge code, persist configuration, and generate 8 emergency recovery codes."""
        if not self.verify_code(secret, code):
            return {"success": False, "message": "Invalid TOTP verification code."}

        # Generate 8 single-use recovery codes (e.g., 8-char uppercase hex)
        backup_codes = [secrets.token_hex(4).upper() for _ in range(8)]
        repo = self._rows(uid)
        repo.delete_where({"uid": int(uid)})
        repo.new_entry({
            "uid": int(uid), "secret_key": encrypt(secret), "is_enabled": 1,
            "backup_codes": ",".join(backup_codes), "created_at": datetime.now().isoformat(),
            "failed_attempts": 0, "locked_until": None,
        })
        return {
            "success": True,
            "backup_codes": backup_codes,
            "message": "Two-factor authentication enabled successfully.",
        }

    def disable_totp(self, uid: int) -> bool:
        """Disable two-factor authentication for the given user."""
        self._rows(uid).delete_where({"uid": int(uid)})
        return True

    def _row(self, uid: int) -> Optional[Dict[str, Any]]:
        row = self._rows(uid).find({"uid": int(uid)})
        if isinstance(row, list):
            row = row[0] if row else None
        return row

    @staticmethod
    def _lock_end(row: Optional[Dict[str, Any]]) -> Optional[datetime]:
        value = (row or {}).get("locked_until")
        try:
            return datetime.strptime(str(value), _TS) if value else None
        except ValueError:
            return None

    def lock_remaining_seconds(self, uid: int) -> int:
        """Seconds until the user may try a code again (0 when not locked)."""
        end = self._lock_end(self._row(uid))
        return max(0, int((end - datetime.now()).total_seconds()) + 1) if end and end > datetime.now() else 0

    def is_locked(self, uid: int) -> bool:
        return self.lock_remaining_seconds(uid) > 0

    def _count_attempt(self, uid: int) -> int:
        """Reserve one attempt (atomic increment, so parallel guesses cannot all see the old count)."""
        from sqlalchemy import func, update
        from sqlalchemy.orm import Session

        from namifax.models.usertotp import UserTOTP

        if isinstance(self.db, Session):
            self.db.execute(update(UserTOTP).where(UserTOTP.uid == int(uid)).values(
                failed_attempts=func.coalesce(UserTOTP.failed_attempts, 0) + 1))
        else:
            self.db.query(f"UPDATE UserTOTP SET failed_attempts = COALESCE(failed_attempts, 0) + 1 WHERE uid = {int(uid)}")
        row = self._row(uid)
        return int((row or {}).get("failed_attempts") or 0)

    def verify_user_login(self, uid: int, code: str) -> bool:
        """Verify user login challenge via TOTP code or single-use backup recovery code.

        Each try is counted before it is checked; after ``MAX_FAILED_ATTEMPTS`` wrong ones the user is locked
        out for ``LOCK_MINUTES`` and even a correct code is refused until then.
        """
        repo = self._rows(uid)
        row = self._row(uid)
        if not row or not _flag(row.get("is_enabled")):
            return True

        end = self._lock_end(row)
        if end and end > datetime.now():
            return False
        if end or row.get("locked_until"):                       # an expired lock: start with a clean count
            repo.update_where({"uid": int(uid)}, {"failed_attempts": 0, "locked_until": None})
            row = {**row, "failed_attempts": 0, "locked_until": None}

        attempts = self._count_attempt(uid)
        if attempts <= MAX_FAILED_ATTEMPTS and self._code_is_valid(repo, row, uid, code):
            repo.update_where({"uid": int(uid)}, {"failed_attempts": 0, "locked_until": None})
            return True

        if attempts >= MAX_FAILED_ATTEMPTS:
            until = (datetime.now() + timedelta(minutes=LOCK_MINUTES)).strftime(_TS)
            repo.update_where({"uid": int(uid)}, {"locked_until": until})
        return False

    def _code_is_valid(self, repo: Any, row: Dict[str, Any], uid: int, code: str) -> bool:
        try:
            secret = decrypt(row.get("secret_key"))
        except (SecretDecryptError, SecretKeyError):
            logging.getLogger("namifax").error("The 2FA seed of user %s cannot be decrypted; check NAMIFAX_SECRET_KEY", uid)
            return False                                     # fail closed
        clean_code = code.strip()

        # 1. Primary TOTP token check
        if secret and self.verify_code(secret, clean_code):
            return True

        # 2. Backup emergency recovery code check (each code works once)
        codes = [c.strip().upper() for c in (row.get("backup_codes") or "").split(",") if c.strip()]
        if clean_code.upper() in codes:
            codes.remove(clean_code.upper())
            repo.update_where({"uid": int(uid)}, {"backup_codes": ",".join(codes)})
            return True
        return False


def _flag(value: Any) -> bool:
    """The legacy engine may hand back 0/1 or text; unknown text is off."""
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "t", "yes")
    return bool(value)
