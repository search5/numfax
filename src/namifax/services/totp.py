import secrets
from datetime import datetime
from typing import Any, Dict, List, Optional
import pyotp
from namifax.db.repository import Repository


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
            "uid": int(uid), "secret_key": secret, "is_enabled": 1,
            "backup_codes": ",".join(backup_codes), "created_at": datetime.now().isoformat(),
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

    def verify_user_login(self, uid: int, code: str) -> bool:
        """Verify user login challenge via TOTP code or single-use backup recovery code."""
        repo = self._rows(uid)
        row = repo.find({"uid": int(uid)})
        if isinstance(row, list):
            row = row[0] if row else None
        if not row or not _flag(row.get("is_enabled")):
            return True

        secret = row.get("secret_key")
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
