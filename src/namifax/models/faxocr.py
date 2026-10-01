"""FaxOCR: recognised fax text for full-text search (B track, group 3)."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from namifax.models.meta import Base

# LONGTEXT on MySQL/MariaDB (a plain TEXT holds only 64 KB there), TEXT elsewhere
LongText = Text().with_variant(mysql.LONGTEXT(), "mysql", "mariadb")


class FaxOCR(Base):
    # The legacy DDL was MySQL-only; it never ran on SQLite, so no OCR text was ever stored there.
    __tablename__ = "FaxOCR"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fax_id: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    fax_file: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ocr_text: Mapped[str] = mapped_column(LongText, nullable=False)
    page_count: Mapped[Optional[int]] = mapped_column(Integer, server_default="1")
    confidence: Mapped[Optional[float]] = mapped_column(Float, server_default="0")
    created_at: Mapped[Optional[str]] = mapped_column(String(32))
