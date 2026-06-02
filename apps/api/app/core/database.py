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
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_lightweight_columns()


def _ensure_lightweight_columns() -> None:
    with engine.begin() as connection:
        dialect_name = connection.dialect.name
        if dialect_name == "sqlite":
            rows = connection.exec_driver_sql("PRAGMA table_info(flow_definitions)").fetchall()
            columns = {row[1] for row in rows}
            if "mapping_definition_id" not in columns:
                connection.exec_driver_sql(
                    "ALTER TABLE flow_definitions ADD COLUMN mapping_definition_id VARCHAR(96)"
                )
            run_rows = connection.exec_driver_sql("PRAGMA table_info(flow_runs)").fetchall()
            run_columns = {row[1] for row in run_rows}
            if "execution_timeline" not in run_columns:
                connection.exec_driver_sql(
                    "ALTER TABLE flow_runs ADD COLUMN execution_timeline JSON DEFAULT '[]' NOT NULL"
                )
        elif dialect_name == "postgresql":
            connection.exec_driver_sql(
                "ALTER TABLE flow_definitions ADD COLUMN IF NOT EXISTS mapping_definition_id VARCHAR(96)"
            )
            connection.exec_driver_sql(
                "ALTER TABLE flow_runs ADD COLUMN IF NOT EXISTS execution_timeline JSONB DEFAULT '[]'::jsonb NOT NULL"
            )


def get_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
