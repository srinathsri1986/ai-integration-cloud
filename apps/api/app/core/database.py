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
    _ensure_tenant_columns()
    _ensure_users_table()
    _ensure_lightweight_columns()
    _ensure_async_execution_columns()


def _ensure_tenant_columns() -> None:
    """Add tenant_id columns to existing tables for older schemas."""
    with engine.begin() as connection:
        dialect_name = connection.dialect.name
        tables_needing_tenant_id = [
            "audit_logs",
            "flow_runs",
            "flow_definitions",
            "mapping_definitions",
        ]
        if dialect_name == "sqlite":
            for table in tables_needing_tenant_id:
                rows = connection.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
                columns = {row[1] for row in rows}
                if "tenant_id" not in columns:
                    connection.exec_driver_sql(
                        f"ALTER TABLE {table} ADD COLUMN tenant_id INTEGER REFERENCES tenants(id)"
                    )
        elif dialect_name == "postgresql":
            for table in tables_needing_tenant_id:
                connection.exec_driver_sql(
                    f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS tenant_id INTEGER REFERENCES tenants(id)"
                )


def _ensure_users_table() -> None:
    """Add columns to users table that may be missing from older schemas."""
    with engine.begin() as connection:
        dialect_name = connection.dialect.name
        if dialect_name == "sqlite":
            rows = connection.exec_driver_sql("PRAGMA table_info(users)").fetchall()
            columns = {row[1] for row in rows}
            if "reset_token_expires_at" not in columns:
                connection.exec_driver_sql(
                    "ALTER TABLE users ADD COLUMN reset_token_expires_at DATETIME"
                )
        elif dialect_name == "postgresql":
            connection.exec_driver_sql(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token_expires_at TIMESTAMPTZ"
            )


def _ensure_async_execution_columns() -> None:
    """Make flow_runs.completed_at nullable to support in-flight running status."""
    with engine.begin() as connection:
        dialect_name = connection.dialect.name
        if dialect_name == "postgresql":
            connection.exec_driver_sql(
                "ALTER TABLE flow_runs ALTER COLUMN completed_at DROP NOT NULL"
            )
        # SQLite does not support ALTER COLUMN; new tables created with nullable constraint.


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
