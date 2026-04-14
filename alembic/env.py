"""Alembic environment bound to SQLAlchemy model metadata."""

from __future__ import annotations

import sys
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from twitch_bot.core.config import get_settings
from database import models as _models  # noqa: F401
from database.base import Base
from database.migrations import normalize_sync_url

config = context.config

# Do not call logging.config.fileConfig here. Loading alembic.ini logging
# (even with disable_existing_loggers=False) replaces root handlers and
# breaks application logging when migrations run inside the bot process.
# Alembic CLI still works with the default Python logging configuration.

target_metadata = Base.metadata


def get_url() -> str:
    """Resolve the database URL from Alembic config or application settings.

    Preference order
    ----------------
    1. ``sqlalchemy.url`` already set on the Alembic config (for example by
       ``run_migrations`` at process startup).
    2. ``get_settings().database_url`` from the application ``.env`` / environment.
    """
    url = config.get_main_option("sqlalchemy.url")
    if url and not url.startswith("driver://"):
        return normalize_sync_url(url)
    return normalize_sync_url(get_settings().database_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
