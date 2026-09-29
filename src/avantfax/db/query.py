"""QueryBuilder and MDBO layer replacing legacy MDBO.php.

Provides programmatic SQL query construction, reflection-free CRUD operations,
and safe parameter handling compatible with AvantFAX schema.
"""

from __future__ import annotations

from typing import Any

from avantfax.db.engine import DatabaseEngine, SQL_ALL

SQL_AND = " AND "
SQL_OR = " OR "

SPECIAL_FUNCTIONS = {
    "CURRENT_TIMESTAMP()",
    "LOCALTIMESTAMP()",
    "LOCALTIME()",
    "CURDATE()",
    "NOW()",
}


class QueryBuilder:
    """SQL Query Builder replacing legacy MDBO class."""

    def __init__(self, engine: DatabaseEngine, quoting: bool = True, debug: bool = False) -> None:
        self.engine = engine
        self.quoting = quoting
        self.debug = debug
        self._last_query: str = ""
        self._num_results: int = 0

    @property
    def num_results(self) -> int:
        return self._num_results

    def set_quoting(self, bool_val: bool) -> None:
        """Enable or disable string quoting."""
        self.quoting = bool_val

    def quote(self, var: Any) -> str:
        """Quote variable, bypassing special SQL time functions."""
        if not self.quoting:
            return f"'{var}'"

        if isinstance(var, str) and var.strip().upper() in SPECIAL_FUNCTIONS:
            return var.strip().upper()

        return self.engine.quote(var)

    def insert(self, table: str, data: dict[str, Any], id_col: str | None = None) -> int | bool:
        """Insert dictionary into table and return last insert id or False."""
        if not data:
            return False

        columns = list(data.keys())
        values = [self.quote(data[c]) for c in columns]

        col_str = ", ".join(columns)
        val_str = ", ".join(values)
        sql = f"INSERT INTO {table} ({col_str}) VALUES ({val_str})"
        self._last_query = sql

        res = self.engine.query(sql)
        if not res.executed:
            return False

        insert_id = self.engine.get_insert_id()
        return insert_id if insert_id is not None else True

    def update(self, table: str, data: dict[str, Any], where: dict[str, Any]) -> bool:
        """Update columns in table matching where conditions."""
        if not data or not where:
            return False

        set_clauses = [f"{col} = {self.quote(val)}" for col, val in data.items()]
        where_clauses = [f"{col} = {self.quote(val)}" for col, val in where.items()]

        set_str = ", ".join(set_clauses)
        where_str = SQL_AND.join(where_clauses)
        sql = f"UPDATE {table} SET {set_str} WHERE {where_str}"
        self._last_query = sql

        res = self.engine.query(sql)
        return res.executed

    def get(self, table: str, id_col: str, id_val: Any) -> dict[str, Any] | None:
        """Fetch single record by primary key."""
        sql = f"SELECT * FROM {table} WHERE {id_col} = {self.quote(id_val)}"
        self._last_query = sql

        res = self.engine.query(sql, fetch_type=SQL_ALL)
        if not res.executed or res.row_count == 0:
            return None

        records = self.engine.get_records()
        return records[0] if records else None

    def find(
        self,
        table: str,
        conditions: dict[str, Any] | None = None,
        logic: str = SQL_AND,
        limit: int | None = None,
        offset: int | None = None,
        reduce_single: bool = True,
    ) -> list[dict[str, Any]] | dict[str, Any] | None:
        """Find records matching given conditions."""
        where_clause = ""
        if conditions:
            clauses = [f"{col} = {self.quote(val)}" for col, val in conditions.items()]
            where_clause = f" WHERE {logic.join(clauses)}"

        sql = f"SELECT * FROM {table}{where_clause}"
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
        if limit is not None and offset is not None:
            sql += f" OFFSET {int(offset)}"

        self._last_query = sql
        res = self.engine.query(sql, fetch_type=SQL_ALL)
        if not res.executed:
            return None

        records = self.engine.get_records()
        self._num_results = len(records)

        if reduce_single and len(records) == 1:
            return records[0]

        return records

    def delete(self, table: str, id_col: str, id_val: Any) -> bool:
        """Delete record matching primary key."""
        sql = f"DELETE FROM {table} WHERE {id_col} = {self.quote(id_val)}"
        self._last_query = sql
        res = self.engine.query(sql)
        return res.executed

    def query(self, sql: str) -> bool:
        """Execute arbitrary SQL query."""
        self._last_query = sql
        res = self.engine.query(sql, fetch_type=SQL_ALL)
        self._num_results = res.row_count
        return res.executed

    def get_records(self) -> list[dict[str, Any]]:
        """Return all fetched records."""
        return self.engine.get_records()

    def get_num_results(self) -> int:
        """Return number of fetched results."""
        return self._num_results

    def get_error(self) -> str | None:
        """Return last error message."""
        return self.engine.get_error()


# Alias for legacy compatibility
MDBO = QueryBuilder
