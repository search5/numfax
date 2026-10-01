"""Database engine provisioning (spec 48).

앱 기동 시 설정에서 SQLAlchemy Engine 을 한 번 만들고, 요청마다 풀의 커넥션을
레거시 호환 ``DatabaseEngine`` 으로 감싸 제공한다. 전역 싱글턴을 쓰지 않는다.
"""

from __future__ import annotations

import os
from typing import Any, Mapping

from sqlalchemy import Engine, create_engine
from sqlalchemy.pool import StaticPool

from namifax.db.engine import DatabaseEngine


def resolve_database_url(settings: Mapping[str, Any] | None, environ: Mapping[str, str]) -> str:
    """Resolve DB URL: settings > DATABASE_URL > AFDB_URL > NAMIFAX_DB_PATH/cwd sqlite file."""
    if settings and settings.get("sqlalchemy.url"):
        return str(settings["sqlalchemy.url"])
    for key in ("DATABASE_URL", "AFDB_URL"):
        if environ.get(key):
            return environ[key]
    db_path = environ.get("NAMIFAX_DB_PATH") or os.path.join(os.getcwd(), "namifax.db")
    return f"sqlite:///{db_path}"


def create_sa_engine(url: str) -> Engine:
    """Create the SQLAlchemy engine; in-memory SQLite shares one DB across connections."""
    if url.startswith("sqlite"):
        kwargs: dict[str, Any] = {"connect_args": {"check_same_thread": False}}
        if url in ("sqlite://", "sqlite:///:memory:"):
            kwargs["poolclass"] = StaticPool
        return create_engine(url, **kwargs)
    return create_engine(url, pool_pre_ping=True)


def open_db(engine: Engine) -> DatabaseEngine:
    """Borrow a pooled connection wrapped as a DatabaseEngine (disconnect() returns it)."""
    return DatabaseEngine.from_connection(engine.raw_connection())
