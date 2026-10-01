"""Settings under the names of the original's local_config.php, read from the environment with the original's defaults."""

from __future__ import annotations

import os
import shutil
from typing import Optional

TRUE = ("1", "true", "True", "yes")


def flag(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    return default if raw is None else raw in TRUE


def text(name: str, default: str) -> str:
    return os.environ.get(name) or default


def number(name: str, default: int) -> int:
    raw = os.environ.get(name, "")
    return int(raw) if raw.isdigit() else default


def hylaspool() -> str:
    return text("HYLASPOOL", "/var/spool/hylafax").rstrip("/") or "/"


def archive_dir() -> str:
    return text("AVANTFAX_ARCHIVE", f"{hylaspool()}/archive")


def sent_dir() -> str:
    return text("ARCHIVE_SENT", f"{hylaspool()}/sent")


def phonebook_path() -> str:
    return text("PHONEBOOK", f"{hylaspool()}/etc/phonebook")


def binary(name: str) -> Optional[str]:
    """Where a program is: the variable named like it (``GS``, ``FAXINFO``...), then BINARYDIR, then the PATH."""
    named = os.environ.get(name.upper().replace("-", "_"))
    if named and os.path.exists(named):
        return named
    folder = os.environ.get("BINARYDIR")
    if folder:
        candidate = os.path.join(folder, name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return shutil.which(name)


def email_date_format() -> str:
    return text("EMAIL_DATE_FORMAT", "%d.%m.%Y %H:%M")


def faxcover_date_format() -> str:
    return text("FAXCOVER_DATE_FORMAT", "%d.%m.%Y %H:%M")


def papersize() -> str:
    return text("PAPERSIZE", "a4")


def dpi() -> int:
    return number("DPI", 200)
