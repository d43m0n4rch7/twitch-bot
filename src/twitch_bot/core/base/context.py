"""Свой контекст команд — используется вместо стандартного commands.Context из TwitchIO."""

from __future__ import annotations

from typing import TYPE_CHECKING

from twitchio.ext import commands

if TYPE_CHECKING:
    from twitch_bot.core.bot import TwitchBot  # noqa: F401


class TwitchContext(commands.Context["TwitchBot"]):
    """Контекст, который команды бота получают вместо стандартного из TwitchIO."""

    @property
    def channel_id(self) -> str:
        """ID канала (broadcaster), в котором сейчас выполняется команда."""
        return self.broadcaster.id
