"""Database engine, session factory, and session dependency.

Schema management is handled exclusively by Alembic migrations.
Run `alembic upgrade head` before starting the application.

For tests, conftest.py calls Base.metadata.create_all() directly on the
SQLite test engine — Alembic is only used against the Postgres runtime DB.
"""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def _database_url() -> str:
    settings = get_settings()
    return settings.database_url


engine = create_engine(_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """Legacy hook kept for test compatibility.

    In production, Alembic manages all schema creation and migrations.
    Tests call this via conftest.py which points DATABASE_URL at SQLite
    and uses Base.metadata.create_all() directly.
    """
    from app.db import models  # noqa: F401

    # Only create tables when running against SQLite (test environment).
    # In production (PostgreSQL), Alembic handles all DDL.
    if engine.dialect.name == "sqlite":
        Base.metadata.create_all(bind=engine)


def get_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
