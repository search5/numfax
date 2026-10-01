import secrets
from datetime import datetime
from typing import Any, Dict, List, Optional
import pyotp
from namifax.db.engine import DatabaseEngine, resolve_db


class TotpService:
    """RFC 6238 Time-based One-Time Password (TOTP) two-factor authentication service."""

    def __init__(self, db: Optional[DatabaseEngine] = None) -> None:
        self.db = resolve_db(db, "TotpService")

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

    def is_totp_enabled(self, uid: int) -> bool:
        """Check whether 2FA is currently active for the given user ID."""
        res = self.db.query(f"SELECT is_enabled FROM UserTOTP WHERE uid = {int(uid)}")
        records = self.db.get_records() if res.executed else []
        if records:
            return bool(records[0].get("is_enabled"))
        return False

    def enable_totp(self, uid: int, secret: str, code: str) -> Dict[str, Any]:
        """Validate challenge code, persist configuration, and generate 8 emergency recovery codes."""
        if not self.verify_code(secret, code):
            return {"success": False, "message": "Invalid TOTP verification code."}

        # Generate 8 single-use recovery codes (e.g., 8-char uppercase hex)
        backup_codes = [secrets.token_hex(4).upper() for _ in range(8)]
        codes_str = ",".join(backup_codes)
        now_str = datetime.now().isoformat()

        # Delete existing if any, then insert
        self.db.query(f"DELETE FROM UserTOTP WHERE uid = {int(uid)}")
        sql = (
            f"INSERT INTO UserTOTP (uid, secret_key, is_enabled, backup_codes, created_at) "
            f"VALUES ({int(uid)}, {self.db.quote(secret)}, 1, {self.db.quote(codes_str)}, {self.db.quote(now_str)})"
        )
        self.db.query(sql)

        return {
            "success": True,
            "backup_codes": backup_codes,
            "message": "Two-factor authentication enabled successfully.",
        }

    def disable_totp(self, uid: int) -> bool:
        """Disable two-factor authentication for the given user."""
        res = self.db.query(f"DELETE FROM UserTOTP WHERE uid = {int(uid)}")
        return res.executed

    def verify_user_login(self, uid: int, code: str) -> bool:
        """Verify user login challenge via TOTP code or single-use backup recovery code."""
        res = self.db.query(
            f"SELECT secret_key, is_enabled, backup_codes FROM UserTOTP WHERE uid = {int(uid)}"
        )
        records = self.db.get_records() if res.executed else []
        if not records:
            return True

        row = records[0]
        if not row.get("is_enabled"):
            return True

        secret = row.get("secret_key")
        clean_code = code.strip()

        # 1. Primary TOTP token check
        if secret and self.verify_code(secret, clean_code):
            return True

        # 2. Backup emergency recovery code check
        raw_backups = row.get("backup_codes") or ""
        codes = [c.strip().upper() for c in raw_backups.split(",") if c.strip()]
        if clean_code.upper() in codes:
            codes.remove(clean_code.upper())
            updated_str = ",".join(codes)
            self.db.query(
                f"UPDATE UserTOTP SET backup_codes = {self.db.quote(updated_str)} WHERE uid = {int(uid)}"
            )
            return True

        return False
