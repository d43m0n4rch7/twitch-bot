"""Custom command context used throughout the bot."""

from __future__ import annotations

from typing import TYPE_CHECKING

from twitchio.ext import commands

if TYPE_CHECKING:
    from twitch_bot.core.bot import TwitchBot  # noqa: F401


class TwitchContext(commands.Context["TwitchBot"]):
    """Application command context bound to :class:`~twitch_bot.core.bot.TwitchBot`.

    Notes
    -----
    The generic parameter is quoted so the import stays type-checking only and
    does not create a runtime cycle with the bot module.
    """

    @property
    def channel_id(self) -> str:
        """Return the broadcaster ID for the channel where the command ran.

        Returns
        -------
        str
            Twitch user ID of the broadcaster.
        """
        return self.broadcaster.id
