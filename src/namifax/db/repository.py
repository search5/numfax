"""Generic repository layer replacing legacy MDBOData.php."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from namifax.db.base import MDBObject
from namifax.db.engine import DatabaseEngine, resolve_db
from namifax.db.query import QueryBuilder, SQL_AND

T = TypeVar("T", bound=MDBObject)


class Repository(Generic[T]):
    """Generic repository managing CRUD and queries for MDBObject entities."""

    def __new__(cls, model_class: Any, db: Any = None):
        # A SQLAlchemy session selects the ORM-backed, database-portable implementation.
        from sqlalchemy.orm import Session

        if isinstance(db, Session):
            from namifax.db.orm_repository import OrmRepository

            return OrmRepository(model_class, db)
        return super().__new__(cls)

    def __init__(self, model_class: type[T] | str, db: DatabaseEngine | None = None) -> None:
        self._db = resolve_db(db, "Repository")
        if isinstance(model_class, str):
            import namifax.models.entities as ent_mod

            if hasattr(ent_mod, model_class):
                self._model_cls: type[T] = getattr(ent_mod, model_class)
            else:
                # Dynamic fallback class
                self._model_cls = type(model_class, (MDBObject,), {"table_name": model_class})  # type: ignore
        else:
            self._model_cls = model_class

        self.data: T = self._model_cls(db=self._db)

    def load(self, id_val: Any) -> bool:
        """Load entity by primary key."""
        if not self._db:
            return False
        self.data = self._model_cls(db=self._db)
        return self.data.load(id_val)

    def new_entry(self, info: dict[str, Any]) -> bool:
        """Create new database entry."""
        if not self._db:
            return False
        self.data = self._model_cls(db=self._db)
        self.data.set_vars(info)
        return self.data.save()

    def update_entry(self, info: dict[str, Any] | None = None) -> bool:
        """Update loaded database entry."""
        if not self._db:
            return False
        if info:
            self.data.set_vars(info)
            pk_col = self.data.get_table_id()
            pk = self.data.get_id()
            if pk is not None:
                qb = QueryBuilder(self._db)
                update_data = {k: v for k, v in info.items() if k != pk_col}
                return qb.update(self.data.get_table_name(), update_data, where={pk_col: pk})
        return self.data.save()

    def delete_entry(self, info: dict[str, Any] | None = None) -> bool:
        """Delete loaded database entry."""
        if not self._db:
            return False
        if info:
            self.data.set_vars(info)
        return self.data.delete()

    def get_info(self) -> dict[str, Any]:
        """Return current entity dictionary."""
        return self.data.to_dict()

    def get_id(self) -> int | None:
        """Return current entity primary key."""
        return self.data.get_id()

    def find(
        self,
        conditions: dict[str, Any] | None = None,
        query_logic: str = SQL_AND,
        limit: int | None = None,
        offset: int | None = None,
        reduce_single: bool = True,
    ) -> list[dict[str, Any]] | dict[str, Any] | None:
        """Query matching entities."""
        if not self._db:
            return None
        qb = QueryBuilder(self._db)
        return qb.find(
            table=self.data.get_table_name(),
            conditions=conditions,
            logic=query_logic,
            limit=limit,
            offset=offset,
            reduce_single=reduce_single,
        )

    def findext(self, conditions: dict[str, Any]) -> list[dict[str, Any]] | dict[str, Any] | None:
        """Find with all conditions."""
        return self.find(conditions=conditions, query_logic=SQL_AND, reduce_single=True)

    def query(self, sql: str, reduce_single: bool = True) -> list[dict[str, Any]] | dict[str, Any] | None:
        """Execute raw SQL through repository."""
        if not self._db:
            return None
        qb = QueryBuilder(self._db)
        if not qb.query(sql):
            return None
        records = qb.get_records()
        if reduce_single and len(records) == 1:
            return records[0]
        return records

    def delete_where(self, conditions: dict[str, Any]) -> int:
        """Delete every row matching all conditions; returns how many. No conditions deletes nothing."""
        if not conditions or any(v is None for v in conditions.values()):
            return 0
        qb = QueryBuilder(self._db)
        where = SQL_AND.join(f"{col} = {qb.quote(val)}" for col, val in conditions.items())
        res = self._db.query(f"DELETE FROM {self.data.get_table_name()} WHERE {where}")
        return int(self._db.affected_rows) if res.executed else 0

    def search_text(self, column: str, text: str, order_by: str | None = None) -> list[dict[str, Any]]:
        """Rows whose ``column`` contains the words of ``text`` in order (case-insensitive, wildcards literal)."""
        import re

        from namifax.db.textsearch import ESCAPE_CHAR, like_pattern

        if not re.fullmatch(r"\w+", column) or (order_by and not re.fullmatch(r"\w+", order_by)):
            raise ValueError("search_text() takes plain column names")
        pattern = self._db.quote(like_pattern(text))
        sql = (f"SELECT * FROM {self.data.get_table_name()} WHERE LOWER({column}) LIKE {pattern} "
               f"ESCAPE '{ESCAPE_CHAR}' ORDER BY {order_by or column}")
        rows = self.query(sql, reduce_single=False)
        return list(rows) if isinstance(rows, list) else []

    def select(
        self,
        columns: list[str] | None = None,
        order_by: str | None = None,
        descending: bool = False,
    ) -> list[dict[str, Any]]:
        """Ordered listing; the same call exists on the ORM repository (portable across databases)."""
        import re

        names = [*(columns or [])] + ([order_by] if order_by else [])
        if any(not re.fullmatch(r"\w+", n) for n in names):
            raise ValueError("select() takes plain column names")
        cols = ", ".join(columns) if columns else "*"
        sql = f"SELECT {cols} FROM {self.data.get_table_name()}"
        if order_by:
            sql += f" ORDER BY {order_by} {'DESC' if descending else 'ASC'}"
        rows = self.query(sql, reduce_single=False)
        return list(rows) if isinstance(rows, list) else []

    def quote(self, val: Any) -> str:
        """Escape and quote value for SQL."""
        if not self._db:
            if val is None:
                return "NULL"
            return f"'{val}'"
        return self._db.quote(val)

    def get_error(self) -> str | None:
        """Return last database error."""
        return self._db.get_error() if self._db else None


# Legacy alias
MDBOData = Repository
