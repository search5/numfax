"""Column types shared by the models."""

from __future__ import annotations

from typing import Any

from datetime import date, datetime

from sqlalchemy import Boolean, String
from sqlalchemy.types import TypeDecorator

_TRUE = {"1", "true", "t", "yes", "y", "on"}


class LegacyBoolean(TypeDecorator):
    """A boolean column that reads every spelling the old code wrote.

    The legacy engine used to store Python booleans as the *text* ``'False'``/``'True'``; a plain
    ``Boolean`` reads any non-empty text as true, so a ``'False'`` in ``superuser`` or ``is_admin`` would
    become a privilege. Reading is therefore done here, on the raw driver value, and unknown text is
    treated as false. DDL and writes are those of an ordinary ``Boolean`` (BOOLEAN / BOOL / BOOLEAN).
    """

    impl = Boolean
    cache_ok = True

    def process_result_value(self, value: Any, dialect: Any) -> bool | None:
        if value is None:
            return None
        if isinstance(value, (bool, int)):
            return bool(value)
        return str(value).strip().lower() in _TRUE

    def result_processor(self, dialect: Any, coltype: Any):
        # bypass the Boolean result processor, which would already have turned 'False' into True
        return lambda value: self.process_result_value(value, dialect)


class IsoText(TypeDecorator):
    """A date/time kept as ISO text (``YYYY-MM-DD HH:MM:SS`` / ``YYYY-MM-DD``) whatever the column is in the database.

    A database written by the original AvantFAX has real ``TIMESTAMP``/``DATE`` columns, which the driver reads as
    ``datetime``/``date`` objects; databases made by this application use ``VARCHAR``. The application works with ISO
    text everywhere (prefix searches, sorting, display), so values are converted on the way in and out.
    """

    impl = String
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(value, date):
            return value.isoformat()
        return value

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(value, date):
            return value.isoformat()
        return value
