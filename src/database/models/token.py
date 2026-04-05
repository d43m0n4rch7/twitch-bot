"""ORM model for persisted Twitch OAuth tokens."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Text, func, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base

if TYPE_CHECKING:
    from database.models.channel import TwitchChannel


class TwitchToken(Base):
    """Persisted Twitch OAuth credentials for a single user.

    Attributes
    ----------
    user_id : str
        Twitch user ID (primary key).
    access_token : str
        Current user access token.
    refresh_token : str
        Current refresh token.
    scopes : list of str
        OAuth scopes granted to the token.
    updated_at : datetime
        Last write time in UTC.
    channel : TwitchChannel or None
        Optional linked channel row.
    """

    __tablename__ = "twitch_tokens"

    user_id: Mapped[str] = mapped_column(Text, primary_key=True)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str] = mapped_column(Text, nullable=False)
    scopes: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        server_default=text("'{}'"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    channel: Mapped[TwitchChannel | None] = relationship(
        "TwitchChannel",
        back_populates="token",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
