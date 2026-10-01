"""Search the SysLog event table through an ORM session."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from namifax.models.syslog import SysLog

MAX_ROWS = 100


class SysLogService:
    """Read access to the ``SysLog`` table for the admin viewer.

    Filters are bound parameters (no string-built SQL). The keyword match is a case-insensitive
    substring match on every database, and ``%`` / ``_`` in the keyword are taken literally.
    """

    def __init__(self, session: Optional[Session] = None) -> None:
        self.session = session

    def _require_session(self) -> Session:
        if self.session is None:
            raise RuntimeError("SysLogService: no database session injected (pass request.dbsession)")
        return self.session

    @staticmethod
    def _date_prefix(day: str, month: str, year: str) -> str:
        """Build the 'YYYY[-MM[-DD]]' prefix from the viewer's drop-downs ('*' means any)."""
        if day and month and year and day != "*" and month != "*" and year != "*":
            d_val = f"{int(day):02d}" if day.isdigit() else day
            m_val = f"{int(month):02d}" if month.isdigit() else month
            return f"{year}-{m_val}-{d_val}"
        if month and year and month != "*" and year != "*":
            m_val = f"{int(month):02d}" if month.isdigit() else month
            return f"{year}-{m_val}"
        if year and year != "*":
            return f"{year}"
        return ""

    def search(self, kw: str = "", day: str = "", month: str = "", year: str = "") -> list[dict[str, str]]:
        session = self._require_session()
        stmt = select(SysLog.logdate, SysLog.logtext)
        if kw:
            stmt = stmt.where(func.lower(SysLog.logtext).contains(kw.lower(), autoescape=True))
        prefix = self._date_prefix(day, month, year)
        if prefix:
            stmt = stmt.where(SysLog.logdate.startswith(prefix, autoescape=True))
        stmt = stmt.order_by(SysLog.logdate.desc(), SysLog.log_id.desc()).limit(MAX_ROWS)
        return [{"logdate": str(r.logdate), "logtext": str(r.logtext)} for r in session.execute(stmt)]
