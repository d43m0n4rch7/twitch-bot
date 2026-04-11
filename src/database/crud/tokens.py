"""CRUD operations for Twitch OAuth tokens."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import TwitchToken


async def get_by_user_id(session: AsyncSession, user_id: str) -> TwitchToken | None:
    """Fetch a token row by Twitch user ID.

    Parameters
    ----------
    session : AsyncSession
        Active SQLAlchemy session.
    user_id : str
        Twitch user ID primary key.

    Returns
    -------
    TwitchToken or None
        Matching row, or ``None`` when absent.
    """
    result = await session.execute(select(TwitchToken).where(TwitchToken.user_id == user_id))
    return result.scalar_one_or_none()


async def get_by_access_token(session: AsyncSession, access_token: str) -> TwitchToken | None:
    """Fetch a token row by access token value.

    Parameters
    ----------
    session : AsyncSession
        Active SQLAlchemy session.
    access_token : str
        Current Twitch access token.

    Returns
    -------
    TwitchToken or None
        Matching row, or ``None`` when absent.
    """
    result = await session.execute(select(TwitchToken).where(TwitchToken.access_token == access_token))
    return result.scalar_one_or_none()


async def list_all(session: AsyncSession) -> Sequence[TwitchToken]:
    """Return every stored token ordered by user ID.

    Parameters
    ----------
    session : AsyncSession
        Active SQLAlchemy session.

    Returns
    -------
    sequence of TwitchToken
        All token rows.
    """
    result = await session.execute(select(TwitchToken).order_by(TwitchToken.user_id))
    return result.scalars().all()


async def list_token_pairs(session: AsyncSession) -> list[tuple[str, str]]:
    """Return ``(access_token, refresh_token)`` pairs ordered by user ID.

    Parameters
    ----------
    session : AsyncSession
        Active SQLAlchemy session.

    Returns
    -------
    list of tuple of str
        Token pairs suitable for TwitchIO ``add_token``.
    """
    result = await session.execute(
        select(TwitchToken.access_token, TwitchToken.refresh_token).order_by(TwitchToken.user_id)
    )
    return [(row.access_token, row.refresh_token) for row in result.all()]


async def upsert(
    session: AsyncSession,
    *,
    user_id: str,
    access_token: str,
    refresh_token: str,
    scopes: Iterable[str] = (),
) -> TwitchToken:
    """Insert or update a token row and return the persisted entity.

    Parameters
    ----------
    session : AsyncSession
        Active SQLAlchemy session.
    user_id : str
        Twitch user ID.
    access_token : str
        Current access token.
    refresh_token : str
        Current refresh token.
    scopes : iterable of str, default ()
        OAuth scopes granted to the token.

    Returns
    -------
    TwitchToken
        Row after the upsert.
    """
    scope_list = list(scopes)
    stmt = (
        insert(TwitchToken)
        .values(
            user_id=user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            scopes=scope_list,
        )
        .on_conflict_do_update(
            index_elements=[TwitchToken.user_id],
            set_={
                "access_token": access_token,
                "refresh_token": refresh_token,
                "scopes": scope_list,
                "updated_at": func.now(),
            },
        )
        .returning(TwitchToken)
    )
    result = await session.execute(stmt)
    token = result.scalar_one()
    await session.flush()
    return token


def _rowcount(result: object) -> int:
    """Return ``rowcount`` when present (CursorResult / DBAPI), else 0."""
    value = getattr(result, "rowcount", None)
    if value is None:
        return 0
    return int(value)



async def delete_by_user_id(session: AsyncSession, user_id: str) -> bool:
    """Delete a token (and cascaded channel) by user ID.

    Parameters
    ----------
    session : AsyncSession
        Active SQLAlchemy session.
    user_id : str
        Twitch user ID primary key.

    Returns
    -------
    bool
        ``True`` when at least one row was deleted.
    """
    result = await session.execute(delete(TwitchToken).where(TwitchToken.user_id == user_id))
    return _rowcount(result) > 0


async def delete_by_access_token(session: AsyncSession, access_token: str) -> bool:
    """Delete a token identified by its access token string.

    Parameters
    ----------
    session : AsyncSession
        Active SQLAlchemy session.
    access_token : str
        Access token value used as lookup key.

    Returns
    -------
    bool
        ``True`` when at least one row was deleted.
    """
    result = await session.execute(delete(TwitchToken).where(TwitchToken.access_token == access_token))
    return _rowcount(result) > 0
