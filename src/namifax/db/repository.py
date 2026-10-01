"""Generic repository layer replacing legacy MDBOData.php."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from namifax.db.base import MDBObject
from namifax.db.engine import DatabaseEngine, resolve_db
from namifax.db.query import QueryBuilder, SQL_AND

T = TypeVar("T", bound=MDBObject)


class Repository(Generic[T]):
    """Generic repository managing CRUD and queries for MDBObject entities."""

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
