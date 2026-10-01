"""namifax encrypt-secrets: encrypt credentials that were stored in plain text before encryption existed.

Converts the cloud storage secret key, the SMTP password and the TOTP seeds. Safe to run repeatedly: values that are
already encrypted are left alone. Needs the same NAMIFAX_SECRET_KEY the application will run with.
"""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import select

from namifax.common.secretbox import SecretKeyError, encrypt, is_encrypted
from namifax.db.provider import cli_session


def run_encrypt_secrets(argv: Sequence[str] | None = None) -> int:
    try:
        encrypt("probe")
    except SecretKeyError as exc:
        print(f"Cannot encrypt: {exc}")
        return 1

    from namifax.models import SystemConfig, SystemSettings, UserTOTP

    converted = {"cloud secret key": 0, "SMTP password": 0, "2FA seeds": 0}
    with cli_session(ensure_schema=True) as session:
        row = session.get(SystemConfig, "cloud_secret_key")
        if row is not None and row.value and not is_encrypted(row.value):
            row.value = encrypt(row.value)
            converted["cloud secret key"] += 1
        for settings in session.execute(select(SystemSettings)).scalars():
            if settings.smtp_password and not is_encrypted(settings.smtp_password):
                settings.smtp_password = encrypt(settings.smtp_password)
                converted["SMTP password"] += 1
        for totp in session.execute(select(UserTOTP)).scalars():
            if totp.secret_key and not is_encrypted(totp.secret_key):
                totp.secret_key = encrypt(totp.secret_key)
                converted["2FA seeds"] += 1
    for what, n in converted.items():
        print(f"{what}: {n} converted")
    return 0
