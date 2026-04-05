"""ORM model for authorized Twitch channels."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, ForeignKey, Index, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base

if TYPE_CHECKING:
    from database.models.token import TwitchToken


class ChannelType(StrEnum):
    """Role of an authorized channel relative to the bot.

    Attributes
    ----------
    owner
        Main channel configured via ``TWITCH_OWNER_ID``.
    bot
        The bot account itself.
    public
        Any other channel that authorized the bot.
    """

    owner = "owner"
    bot = "bot"
    public = "public"


class TwitchChannel(Base):
    """Channel that has authorized the bot and may receive EventSub traffic.

    Attributes
    ----------
    user_id : str
        Twitch user ID; foreign key to :class:`~database.models.token.TwitchToken`.
    login : str or None
        Twitch login name when known.
    display_name : str or None
        Twitch display name when known.
    channel_type : ChannelType
        One of ``owner``, ``bot`` or ``public``.
    is_active : bool
        Whether the channel is currently treated as authorized.
    created_at : datetime
        Row creation time in UTC.
    updated_at : datetime
        Last write time in UTC.
    token : TwitchToken
        Linked OAuth token row.
    """

    __tablename__ = "twitch_channels"
    __table_args__ = (
        CheckConstraint(
            "channel_type IN ('owner', 'bot', 'public')",
            name="twitch_channels_channel_type_check",
        ),
        Index(
            "twitch_channels_active_idx",
            "is_active",
            postgresql_where=text("is_active = true"),
        ),
    )

    user_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("twitch_tokens.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    login: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    channel_type: Mapped[ChannelType] = mapped_column(
        Enum(
            ChannelType,
            name="channel_type",
            values_callable=lambda enum: [member.value for member in enum],
            native_enum=False,
            validate_strings=True,
        ),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    token: Mapped[TwitchToken] = relationship(
        "TwitchToken",
        back_populates="channel",
    )
