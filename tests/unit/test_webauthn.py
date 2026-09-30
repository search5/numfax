from unittest.mock import MagicMock, patch
import pytest
from namifax.services.webauthn import WebAuthnService, WebAuthnCredential

def test_webauthn_service_init():
    svc = WebAuthnService(rp_id="fax.example.com", rp_name="NamiFAX Enterprise")
    assert svc.rp_id == "fax.example.com"
    assert svc.rp_name == "NamiFAX Enterprise"

def test_generate_registration_options():
    svc = WebAuthnService(rp_id="fax.example.com", rp_name="NamiFAX Enterprise")
    opts = svc.generate_registration_options(
        user_id=1,
        user_name="admin",
        user_display_name="Administrator",
    )
    assert "challenge" in opts
    assert opts["rp"]["name"] == "NamiFAX Enterprise"
    assert opts["rp"]["id"] == "fax.example.com"
    assert opts["user"]["name"] == "admin"
    assert opts["user"]["displayName"] == "Administrator"
    assert len(opts["pubKeyCredParams"]) > 0

def test_generate_authentication_options():
    svc = WebAuthnService(rp_id="fax.example.com", rp_name="NamiFAX Enterprise")
    from webauthn.helpers import bytes_to_base64url
    test_id = bytes_to_base64url(b"test_credential_id_123")
    mock_db = MagicMock()
    mock_db.query.return_value = [
        {"credential_id": test_id, "transports": "internal"}
    ]
    with patch.object(svc, "db", mock_db):
        opts = svc.generate_authentication_options(user_id=1)
        assert "challenge" in opts
        assert opts["rpId"] == "fax.example.com"
        assert len(opts["allowCredentials"]) == 1
        assert opts["allowCredentials"][0]["id"] == test_id

def test_list_and_delete_credentials():
    svc = WebAuthnService()
    mock_db = MagicMock()
    mock_db.query.return_value = [
        {
            "id": 10,
            "uid": 1,
            "credential_id": "cred_id_10",
            "device_name": "MacBook Touch ID",
            "created_at": "2026-10-01 00:00:00",
            "last_used_at": None,
            "sign_count": 0,
        }
    ]
    with patch.object(svc, "db", mock_db):
        creds = svc.list_credentials(uid=1)
        assert len(creds) == 1
        assert creds[0].device_name == "MacBook Touch ID"
        assert creds[0].credential_id == "cred_id_10"

        success = svc.delete_credential(uid=1, credential_db_id=10)
        assert success is True
        mock_db.query.assert_called()

def test_save_credential():
    svc = WebAuthnService()
    mock_db = MagicMock()
    with patch.object(svc, "db", mock_db):
        cred = svc.save_credential(
            uid=1,
            credential_id="cred_new_123",
            public_key="pubkey_hex_or_b64",
            sign_count=1,
            device_name="YubiKey 5C",
            transports=["usb", "nfc"],
        )
        assert cred.credential_id == "cred_new_123"
        assert cred.device_name == "YubiKey 5C"
        mock_db.query.assert_called()
