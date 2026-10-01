"""Column types shared by the models."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean
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
