"""CRUD operations for authorized Twitch channels."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ChannelType, TwitchChannel


async def get_by_user_id(session: AsyncSession, user_id: str) -> TwitchChannel | None:
    """Fetch a channel row by Twitch user ID.

    Parameters
    ----------
    session : AsyncSession
        Active SQLAlchemy session.
    user_id : str
        Twitch user ID primary key.

    Returns
    -------
    TwitchChannel or None
        Matching row, or ``None`` when absent.
    """
    result = await session.execute(select(TwitchChannel).where(TwitchChannel.user_id == user_id))
    return result.scalar_one_or_none()


async def list_active(
    session: AsyncSession,
    *,
    exclude: Iterable[str] = (),
    channel_types: Iterable[ChannelType] | None = None,
) -> Sequence[TwitchChannel]:
    """List active channels with optional filters.

    Parameters
    ----------
    session : AsyncSession
        Active SQLAlchemy session.
    exclude : iterable of str, default ()
        User IDs to omit from the result.
    channel_types : iterable of ChannelType or None, default None
        When set, only rows with these types are returned.

    Returns
    -------
    sequence of TwitchChannel
        Matching active channels ordered by user ID.
    """
    stmt = select(TwitchChannel).where(TwitchChannel.is_active.is_(True)).order_by(TwitchChannel.user_id)
    if channel_types is not None:
        stmt = stmt.where(TwitchChannel.channel_type.in_(list(channel_types)))
    result = await session.execute(stmt)
    channels = result.scalars().all()
    excluded = set(exclude)
    if not excluded:
        return channels
    return [channel for channel in channels if channel.user_id not in excluded]


async def list_active_user_ids(session: AsyncSession, *, exclude: Iterable[str] = ()) -> list[str]:
    """Return user IDs of active channels.

    Parameters
    ----------
    session : AsyncSession
        Active SQLAlchemy session.
    exclude : iterable of str, default ()
        User IDs to omit from the result.

    Returns
    -------
    list of str
        Active channel user IDs.
    """
    channels = await list_active(session, exclude=exclude)
    return [channel.user_id for channel in channels]


async def upsert(
    session: AsyncSession,
    *,
    user_id: str,
    channel_type: ChannelType | str,
    login: str | None = None,
    display_name: str | None = None,
    is_active: bool = True,
) -> TwitchChannel:
    """Insert or update a channel linked to an existing token.

    Parameters
    ----------
    session : AsyncSession
        Active SQLAlchemy session.
    user_id : str
        Twitch user ID (must already exist in ``twitch_tokens``).
    channel_type : ChannelType or str
        Channel role relative to the bot.
    login : str or None, default None
        Twitch login; when ``None`` on update, the previous value is kept.
    display_name : str or None, default None
        Display name; when ``None`` on update, the previous value is kept.
    is_active : bool, default True
        Whether the channel should be treated as authorized.

    Returns
    -------
    TwitchChannel
        Row after the upsert.
    """
    if isinstance(channel_type, str):
        channel_type = ChannelType(channel_type)

    values: dict[str, object] = {
        "user_id": user_id,
        "channel_type": channel_type,
        "is_active": is_active,
    }
    if login is not None:
        values["login"] = login
    if display_name is not None:
        values["display_name"] = display_name

    update_set: dict[str, object] = {
        "channel_type": channel_type,
        "is_active": is_active,
        "updated_at": func.now(),
    }
    if login is not None:
        update_set["login"] = login
    if display_name is not None:
        update_set["display_name"] = display_name

    stmt = (
        insert(TwitchChannel)
        .values(**values)
        .on_conflict_do_update(
            index_elements=[TwitchChannel.user_id],
            set_=update_set,
        )
        .returning(TwitchChannel)
    )
    result = await session.execute(stmt)
    channel = result.scalar_one()
    await session.flush()
    return channel


def _rowcount(result: object) -> int:
    """Return ``rowcount`` when present (CursorResult / DBAPI), else 0."""
    value = getattr(result, "rowcount", None)
    if value is None:
        return 0
    return int(value)



async def set_active(session: AsyncSession, user_id: str, *, is_active: bool) -> bool:
    """Set the active flag for a channel.

    Parameters
    ----------
    session : AsyncSession
        Active SQLAlchemy session.
    user_id : str
        Twitch user ID primary key.
    is_active : bool
        New active flag value.

    Returns
    -------
    bool
        ``True`` when a row was updated.
    """
    result = await session.execute(
        update(TwitchChannel)
        .where(TwitchChannel.user_id == user_id)
        .values(is_active=is_active, updated_at=func.now())
    )
    return _rowcount(result) > 0


async def deactivate(session: AsyncSession, user_id: str) -> bool:
    """Mark a channel inactive without deleting its token.

    Parameters
    ----------
    session : AsyncSession
        Active SQLAlchemy session.
    user_id : str
        Twitch user ID primary key.

    Returns
    -------
    bool
        ``True`` when a row was updated.
    """
    return await set_active(session, user_id, is_active=False)


async def delete_by_user_id(session: AsyncSession, user_id: str) -> bool:
    """Delete a channel row by user ID.

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
    result = await session.execute(delete(TwitchChannel).where(TwitchChannel.user_id == user_id))
    return _rowcount(result) > 0
