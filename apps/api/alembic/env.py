"""Alembic migration environment.

Uses the synchronous SQLAlchemy engine that matches the app's database.py.
The database URL is read from app settings so it is consistent with the
runtime configuration — no duplicate connection string.
"""

import logging
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger("alembic.env")

# Import the app's DeclarativeBase so Alembic can see all models.
# The side-effect of importing models registers them with Base.metadata.
from app.core.database import Base  # noqa: E402
import app.db.models  # noqa: F401, E402 — registers all ORM models

target_metadata = Base.metadata


def _get_url() -> str:
    """Read the database URL from the application settings at runtime."""
    from app.core.config import get_settings

    return get_settings().database_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no DB connection required, outputs SQL)."""
    url = _get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database connection."""
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = _get_url()

    connectable = engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
