"""Modern Database Engine layer replacing legacy SQL.php.

Provides connection pooling, dialect abstraction (MySQL / SQLite),
transaction management, and query execution.
"""

from __future__ import annotations

import contextlib
import html
import re
import sqlite3
from dataclasses import dataclass
from typing import Any, Iterator, Sequence

SQL_NONE = 1
SQL_ALL = 2


@dataclass
class QueryResult:
    executed: bool
    row_count: int = 0
    affected_rows: int = 0


class DatabaseEngine:
    """Database abstraction engine compatible with AvantFAX legacy SQL semantics."""

    def __init__(self, debug: bool = False) -> None:
        self.debug = debug
        self._conn: sqlite3.Connection | Any = None
        self._cursor: sqlite3.Cursor | Any = None
        self._records: list[dict[str, Any]] = []
        self._current_iter: Iterator[dict[str, Any]] | None = None
        self._last_query: str = ""
        self._last_insert_id: int | None = None
        self._affected_rows: int = 0
        self._error: str | None = None

    @property
    def affected_rows(self) -> int:
        return self._affected_rows

    def connect(
        self,
        db_user: str,
        db_pass: str,
        db_name: str,
        db_host: str = "localhost",
        db_engine: str = "mysql",
    ) -> bool:
        """Establish database connection."""
        self._error = None
        try:
            if db_engine == "sqlite":
                return self.connect_sqlite(db_name)

            # Attempt importing pymysql or mysql.connector if available
            try:
                import pymysql  # type: ignore

                self._conn = pymysql.connect(
                    host=db_host,
                    user=db_user,
                    password=db_pass,
                    database=db_name,
                    charset="utf8mb4",
                    cursorclass=pymysql.cursors.DictCursor,
                    autocommit=True,
                )
                self._cursor = self._conn.cursor()
                return True
            except ImportError:
                # Fallback to sqlite wrapper for dev/testing when MySQL driver not installed
                self._error = "MySQL driver (pymysql) not installed"
                return False
        except Exception as exc:
            self._error = str(exc)
            return False

    def connect_sqlite(self, path: str = ":memory:") -> bool:
        """Connect to SQLite database for testing and embedded deployment."""
        self._error = None
        try:
            self._conn = sqlite3.connect(path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._cursor = self._conn.cursor()
            return True
        except Exception as exc:
            self._error = str(exc)
            return False

    def disconnect(self) -> None:
        """Close active connection."""
        if self._cursor:
            with contextlib.suppress(Exception):
                self._cursor.close()
        if self._conn:
            with contextlib.suppress(Exception):
                self._conn.close()
        self._conn = None
        self._cursor = None

    def __del__(self) -> None:
        self.disconnect()

    def query(
        self,
        sql: str,
        params: Sequence[Any] | dict[str, Any] | None = None,
        fetch_type: int = SQL_NONE,
    ) -> QueryResult:
        """Execute SQL query."""
        if not self._conn:
            self._error = "No active database connection"
            return QueryResult(executed=False)

        self._records = []
        self._current_iter = None
        self._last_query = sql
        self._error = None

        if self.debug:
            print(f"[SQL DEBUG] {sql}")

        is_select = bool(re.match(r"^\s*SELECT", sql, re.IGNORECASE))

        try:
            if params:
                self._cursor.execute(sql, params)
            else:
                self._cursor.execute(sql)

            if is_select:
                rows = self._cursor.fetchall()
                # Convert sqlite3.Row or tuple to dict
                self._records = [dict(row) for row in rows]
                row_count = len(self._records)
                self._affected_rows = 0

                if fetch_type == SQL_NONE:
                    self._current_iter = iter(self._records)

                return QueryResult(executed=True, row_count=row_count)
            else:
                self._conn.commit()
                self._affected_rows = self._cursor.rowcount
                self._last_insert_id = self._cursor.lastrowid
                return QueryResult(executed=True, affected_rows=self._affected_rows)
        except Exception as exc:
            self._error = str(exc)
            if self.debug:
                print(f"[SQL ERROR] {self._error}")
            return QueryResult(executed=False)

    def get_records(self) -> list[dict[str, Any]]:
        """Return all fetched records."""
        return self._records

    def get_result(self) -> dict[str, Any] | bool:
        """Fetch next record, or False when exhausted."""
        if self._current_iter is None:
            self._current_iter = iter(self._records)

        try:
            return next(self._current_iter)
        except StopIteration:
            return False

    def get_insert_id(self) -> int | None:
        """Return last inserted autoincrement ID."""
        return self._last_insert_id

    def get_last_query(self) -> str:
        """Return last executed query string."""
        return self._last_query

    def get_error(self) -> str | None:
        """Return last error message."""
        return self._error

    def quote(self, string: Any) -> str:
        """Quote literal string safely."""
        if string is None:
            return "NULL"
        escaped = str(string).replace("'", "''")
        return f"'{escaped}'"

    def gen_xml(
        self,
        xml_title: bool = True,
        mysql_style: bool | str = False,
        root_tag: str = "response",
        row_tag: str = "row",
        html_entities: bool = True,
    ) -> str:
        """Generate XML string from current records matching legacy AvantFAX genXML."""
        if not self._records:
            return "<noelement></noelement>"

        lines: list[str] = []
        if xml_title:
            lines.append('<?xml version="1.0" encoding="utf-8" ?>')

        actual_root = "resultset" if mysql_style is True else root_tag
        if mysql_style is True:
            statement_attr = html.escape(self._last_query, quote=True)
            lines.append(f'<{actual_root} statement="{statement_attr}">')
        else:
            lines.append(f"<{actual_root}>")

        for rec in self._records:
            lines.append(f"<{row_tag}>")
            for k, v in rec.items():
                val_str = "" if v is None else str(v)
                if html_entities:
                    val_str = html.escape(val_str, quote=True)
                val_str = self.fix_amp(val_str)
                if mysql_style is True:
                    lines.append(f'<field name="{k}">{val_str}</field>')
                else:
                    lines.append(f"<{k}>{val_str}</{k}>")
            lines.append(f"</{row_tag}>")

        lines.append(f"</{actual_root}>")
        return "\n".join(lines)

    @staticmethod
    def fix_amp(content: str) -> str:
        """Fix double-escaped ampersands."""
        return content.replace("&amp;amp;", "&amp;")

    @contextlib.contextmanager
    def transaction(self) -> Iterator[Any]:
        """Transactional context manager."""
        if not self._conn:
            raise RuntimeError("Database not connected")
        try:
            yield self._cursor
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise


def get_default_engine() -> DatabaseEngine:
    """Retrieve default DatabaseEngine from namifax application layer."""
    from namifax.db.engine import get_default_engine as _get_default_engine
    return _get_default_engine()
