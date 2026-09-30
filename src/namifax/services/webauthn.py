from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import webauthn
from webauthn.helpers import (
    base64url_to_bytes,
    options_to_json,
)
from webauthn.helpers.structs import (
    AttestationConveyancePreference,
    AuthenticatorAttachment,
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    UserVerificationRequirement,
)

from avantfax.db.engine import DatabaseEngine

@dataclass
class WebAuthnCredential:
    id: int
    uid: int
    credential_id: str
    device_name: str
    created_at: str | datetime
    last_used_at: str | datetime | None = None
    sign_count: int = 0
    transports: str | None = None

class WebAuthnService:
    """Enterprise W3C WebAuthn / FIDO2 Passkeys authentication service."""

    def __init__(
        self,
        rp_id: str = "localhost",
        rp_name: str = "NamiFAX Enterprise",
        origin: str = "http://localhost:8000",
    ) -> None:
        self.rp_id = rp_id
        self.rp_name = rp_name
        self.origin = origin
        self.db = DatabaseEngine()
        self._ensure_table_exists()

    def _ensure_table_exists(self) -> None:
        create_sql = """
        CREATE TABLE IF NOT EXISTS UserWebAuthnCredentials (
            id INT AUTO_INCREMENT PRIMARY KEY,
            uid INT NOT NULL,
            credential_id VARCHAR(255) NOT NULL UNIQUE,
            public_key TEXT NOT NULL,
            sign_count INT DEFAULT 0,
            transports VARCHAR(100) DEFAULT NULL,
            device_name VARCHAR(100) NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_used_at DATETIME NULL,
            INDEX idx_webauthn_uid (uid)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
        try:
            self.db.query(create_sql)
        except Exception:
            pass

    def generate_registration_options(
        self,
        user_id: int,
        user_name: str,
        user_display_name: str | None = None,
    ) -> dict[str, Any]:
        """Generate options for navigator.credentials.create()."""
        raw_options = webauthn.generate_registration_options(
            rp_id=self.rp_id,
            rp_name=self.rp_name,
            user_id=str(user_id).encode("utf-8"),
            user_name=user_name,
            user_display_name=user_display_name or user_name,
            attestation=AttestationConveyancePreference.NONE,
            authenticator_selection=AuthenticatorSelectionCriteria(
                user_verification=UserVerificationRequirement.PREFERRED,
            ),
        )
        return json.loads(options_to_json(raw_options))

    def verify_registration_response(
        self,
        credential_data: dict[str, Any] | str,
        expected_challenge: str,
        expected_origin: str | None = None,
    ) -> dict[str, Any]:
        """Verify client registration attestation and extract credential details."""
        if isinstance(credential_data, str):
            credential_data = json.loads(credential_data)

        verification = webauthn.verify_registration_response(
            credential=credential_data,
            expected_challenge=base64url_to_bytes(expected_challenge),
            expected_rp_id=self.rp_id,
            expected_origin=expected_origin or self.origin,
            require_user_verification=False,
        )
        return {
            "credential_id": verification.credential_id.decode("utf-8") if isinstance(verification.credential_id, bytes) else str(verification.credential_id),
            "credential_public_key": verification.credential_public_key.hex(),
            "sign_count": verification.sign_count,
        }

    def generate_authentication_options(
        self,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        """Generate options for navigator.credentials.get()."""
        allow_creds = []
        if user_id:
            try:
                rows = self.db.query(
                    f"SELECT credential_id, transports FROM UserWebAuthnCredentials WHERE uid = {int(user_id)}"
                )
                if rows:
                    for row in rows:
                        cid = row.get("credential_id")
                        if cid:
                            allow_creds.append(
                                PublicKeyCredentialDescriptor(
                                    id=base64url_to_bytes(cid) if isinstance(cid, str) else cid
                                )
                            )
            except Exception:
                pass

        raw_options = webauthn.generate_authentication_options(
            rp_id=self.rp_id,
            allow_credentials=allow_creds if allow_creds else None,
            user_verification=UserVerificationRequirement.PREFERRED,
        )
        return json.loads(options_to_json(raw_options))

    def verify_authentication_response(
        self,
        credential_data: dict[str, Any] | str,
        expected_challenge: str,
        credential_public_key: bytes,
        credential_current_sign_count: int,
        expected_origin: str | None = None,
    ) -> int:
        """Verify client authentication assertion and return updated sign count."""
        if isinstance(credential_data, str):
            credential_data = json.loads(credential_data)

        verification = webauthn.verify_authentication_response(
            credential=credential_data,
            expected_challenge=base64url_to_bytes(expected_challenge),
            expected_rp_id=self.rp_id,
            expected_origin=expected_origin or self.origin,
            credential_public_key=credential_public_key,
            credential_current_sign_count=credential_current_sign_count,
            require_user_verification=False,
        )
        return verification.new_sign_count

    def save_credential(
        self,
        uid: int,
        credential_id: str,
        public_key: str,
        sign_count: int = 0,
        device_name: str = "Security Key",
        transports: list[str] | str | None = None,
    ) -> WebAuthnCredential:
        """Save a new WebAuthn credential in database."""
        if isinstance(transports, list):
            transports_str = ",".join(transports)
        else:
            transports_str = transports or ""

        q_cid = self.db.quote(credential_id)
        q_pk = self.db.quote(public_key)
        q_name = self.db.quote(device_name)
        q_tr = self.db.quote(transports_str)

        sql = f"""
        INSERT INTO UserWebAuthnCredentials (uid, credential_id, public_key, sign_count, transports, device_name)
        VALUES ({int(uid)}, {q_cid}, {q_pk}, {int(sign_count)}, {q_tr}, {q_name})
        """
        self.db.query(sql)

        return WebAuthnCredential(
            id=0,
            uid=uid,
            credential_id=credential_id,
            device_name=device_name,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            sign_count=sign_count,
            transports=transports_str,
        )

    def list_credentials(self, uid: int) -> list[WebAuthnCredential]:
        """List all active credentials registered by a user."""
        try:
            rows = self.db.query(
                f"SELECT id, uid, credential_id, device_name, created_at, last_used_at, sign_count, transports "
                f"FROM UserWebAuthnCredentials WHERE uid = {int(uid)} ORDER BY id DESC"
            )
            if not rows:
                return []
            return [
                WebAuthnCredential(
                    id=row.get("id", 0),
                    uid=row.get("uid", uid),
                    credential_id=row.get("credential_id", ""),
                    device_name=row.get("device_name", "Security Key"),
                    created_at=str(row.get("created_at", "")),
                    last_used_at=str(row.get("last_used_at", "")) if row.get("last_used_at") else None,
                    sign_count=row.get("sign_count", 0),
                    transports=row.get("transports"),
                )
                for row in rows
            ]
        except Exception:
            return []

    def delete_credential(self, uid: int, credential_db_id: int) -> bool:
        """Delete a credential registered by user."""
        try:
            self.db.query(
                f"DELETE FROM UserWebAuthnCredentials WHERE id = {int(credential_db_id)} AND uid = {int(uid)}"
            )
            return True
        except Exception:
            return False

    def get_credential_by_id(self, credential_id: str) -> dict[str, Any] | None:
        """Fetch credential row by base64url credential_id."""
        try:
            q_cid = self.db.quote(credential_id)
            rows = self.db.query(
                f"SELECT * FROM UserWebAuthnCredentials WHERE credential_id = {q_cid} LIMIT 1"
            )
            if rows:
                return rows[0]
            return None
        except Exception:
            return None

    def update_sign_count(self, credential_id: str, new_sign_count: int) -> None:
        """Update sign count and last used timestamp."""
        try:
            q_cid = self.db.quote(credential_id)
            self.db.query(
                f"UPDATE UserWebAuthnCredentials SET sign_count = {int(new_sign_count)}, "
                f"last_used_at = NOW() WHERE credential_id = {q_cid}"
            )
        except Exception:
            pass
