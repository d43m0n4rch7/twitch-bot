"""Alembic migration helpers used at process startup."""

from __future__ import annotations

from pathlib import Path

# src/database/migrations.py -> project root is parents[2]
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def normalize_sync_url(url: str) -> str:
    """Normalize a Postgres URL to the ``postgresql+psycopg`` form for Alembic.

    Parameters
    ----------
    url : str
        Connection URI as provided by configuration.

    Returns
    -------
    str
        Sync SQLAlchemy URL using the psycopg driver.
    """
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql+asyncpg://"):
        url = "postgresql://" + url[len("postgresql+asyncpg://") :]
    if url.startswith("postgresql+psycopg://"):
        return url
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


def run_migrations(database_url: str) -> None:
    """Apply pending Alembic migrations up to ``head``.

    Parameters
    ----------
    database_url : str
        PostgreSQL connection URI from application settings.

    Notes
    -----
    Uses a bare ``Config()`` (no ``alembic.ini`` path) so Alembic does not load
    the ini logging section and cannot rewrite handlers configured in ``main``.
    ``script_location`` and ``sqlalchemy.url`` are set explicitly.
    """
    from alembic import command
    from alembic.config import Config

    config = Config()
    config.set_main_option("script_location", str(_PROJECT_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", normalize_sync_url(database_url))
    command.upgrade(config, "head")
