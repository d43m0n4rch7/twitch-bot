"""Async SQLAlchemy engine and session factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def normalize_async_url(url: str) -> str:
    """Normalize a Postgres URL to the ``postgresql+asyncpg`` SQLAlchemy form.

    Parameters
    ----------
    url : str
        Connection URI as provided by configuration (any common Postgres scheme).

    Returns
    -------
    str
        URL suitable for :func:`sqlalchemy.ext.asyncio.create_async_engine`.
    """
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql+psycopg://"):
        url = "postgresql+asyncpg://" + url[len("postgresql+psycopg://") :]
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://") :]
    return url


def create_engine(database_url: str, *, echo: bool = False) -> AsyncEngine:
    """Create an async SQLAlchemy engine.

    Parameters
    ----------
    database_url : str
        PostgreSQL connection URI.
    echo : bool, default False
        Forwarded to SQLAlchemy to log SQL statements.

    Returns
    -------
    AsyncEngine
        Configured asynchronous engine.

    Notes
    -----
    ``statement_cache_size=0`` is required for Supabase transaction poolers
    that reject prepared statements.
    """
    return create_async_engine(
        normalize_async_url(database_url),
        echo=echo,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        connect_args={"statement_cache_size": 0},
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create a session factory bound to ``engine``.

    Parameters
    ----------
    engine : AsyncEngine
        Engine returned by :func:`create_engine`.

    Returns
    -------
    async_sessionmaker of AsyncSession
        Factory that produces short-lived sessions.
    """
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Database:
    """Application-scoped holder for the async engine and session factory.

    Parameters
    ----------
    database_url : str
        PostgreSQL connection URI.
    echo : bool, default False
        Whether SQLAlchemy should echo SQL to the logger.
    """

    def __init__(self, database_url: str, *, echo: bool = False) -> None:
        self.engine = create_engine(database_url, echo=echo)
        self.session_factory = create_session_factory(self.engine)

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Yield a session that commits on success and rolls back on error.

        Yields
        ------
        AsyncSession
            Open SQLAlchemy session bound to this database.
        """
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def close(self) -> None:
        """Dispose the underlying engine and release connection pool resources."""
        await self.engine.dispose()
