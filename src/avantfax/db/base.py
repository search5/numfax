"""ORM ActiveRecord base layer replacing legacy MDBObject.php and afDB."""

from __future__ import annotations

from typing import Any

from avantfax.db.engine import DatabaseEngine
from avantfax.db.query import QueryBuilder


class MDBObject:
    """ActiveRecord-compatible base class for AvantFAX database entities."""

    table_name: str = ""
    table_id_name: str = "id"

    def __init__(self, db: DatabaseEngine | None = None) -> None:
        self._db = db
        self._debug = False

    def get_table_name(self) -> str:
        """Return table name or class name."""
        return self.table_name or self.__class__.__name__

    def get_table_id(self) -> str:
        """Return primary key column name."""
        return self.table_id_name

    def get_db(self) -> DatabaseEngine | None:
        """Return bound DatabaseEngine."""
        return self._db

    def set_db(self, db: DatabaseEngine) -> None:
        """Bind DatabaseEngine."""
        self._db = db

    def get_id(self) -> int | None:
        """Return primary key value."""
        val = getattr(self, self.get_table_id(), None)
        try:
            return int(val) if val is not None else None
        except (ValueError, TypeError):
            return None

    def set_id(self, id_val: Any) -> bool:
        """Set primary key value with numeric validation."""
        try:
            int_val = int(id_val)
            setattr(self, self.get_table_id(), int_val)
            return True
        except (ValueError, TypeError):
            return False

    def set_vars(self, vals: dict[str, Any]) -> None:
        """Inject column dictionary values into instance attributes."""
        for key, val in vals.items():
            setattr(self, key, val)

    def to_dict(self, include_none: bool = False) -> dict[str, Any]:
        """Serialize instance fields to dictionary, excluding internal attributes and optionally None values."""
        ignored = {"table_name", "table_id_name"}
        result: dict[str, Any] = {}
        for k, v in self.__dict__.items():
            if not k.startswith("_") and k not in ignored and not callable(v):
                if include_none or v is not None:
                    result[k] = v
        return result

    def load(self, id_val: Any) -> bool:
        """Load record from database by primary key."""
        if not self._db:
            return False
        qb = QueryBuilder(self._db)
        rec = qb.get(self.get_table_name(), self.get_table_id(), id_val)
        if rec:
            self.set_vars(rec)
            return True
        return False

    def save(self) -> bool:
        """Insert or update current instance in database."""
        if not self._db:
            return False
        qb = QueryBuilder(self._db)
        data = self.to_dict(include_none=False)
        pk = self.get_id()
        if pk is not None:
            # Update
            return qb.update(self.get_table_name(), data, where={self.get_table_id(): pk})
        else:
            # Insert - ensure PK is not in data if None
            pk_col = self.get_table_id()
            if pk_col in data and data[pk_col] is None:
                del data[pk_col]
            res = qb.insert(self.get_table_name(), data, id_col=pk_col)
            if res:
                if isinstance(res, int):
                    self.set_id(res)
                return True
            return False

    def delete(self) -> bool:
        """Delete current instance from database."""
        if not self._db:
            return False
        pk = self.get_id()
        if pk is None:
            return False
        qb = QueryBuilder(self._db)
        return qb.delete(self.get_table_name(), self.get_table_id(), pk)


# Legacy alias
afDB = MDBObject
