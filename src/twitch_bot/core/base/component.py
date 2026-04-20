"""Base component classes for access-controlled bot features."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from twitchio.ext import commands

if TYPE_CHECKING:
    from twitch_bot.core.bot import TwitchBot

__all__ = ["AccessDeniedError", "OwnerOnlyComponent", "PublicComponent", "TwitchComponent"]


class AccessDeniedError(Exception):
    """Raised by a component guard when a command must be rejected.

    Parameters
    ----------
    message : str
        Human-readable reason shown to the chatter unless ``silent`` is true.
    silent : bool, default False
        When true, the global command error handler must not reply in chat.
    """

    def __init__(self, message: str, *, silent: bool = False) -> None:
        super().__init__(message)
        self.silent = silent


class TwitchComponent(commands.Component):
    """Base component that keeps a reference to the parent bot.

    Parameters
    ----------
    bot : TwitchBot
        Running application bot that owns this component.
    """

    def __init__(self, bot: TwitchBot) -> None:
        self.bot = bot


class PublicComponent(TwitchComponent):
    """Base for commands and listeners available in any authorized channel."""


class OwnerOnlyComponent(TwitchComponent):
    """Base for commands restricted to the bot owner's own channel."""

    @override
    async def component_before_invoke(self, ctx: commands.Context[Any]) -> None:
        """Reject commands invoked outside the owner's channel.

        Parameters
        ----------
        ctx : commands.Context
            Invocation context provided by TwitchIO.

        Raises
        ------
        AccessDeniedError
            If the command was not invoked in the owner's channel.
        """
        if ctx.broadcaster.id != self.bot.owner_id:
            raise AccessDeniedError(
                "This command is only available in the owner's channel.",
                silent=True,
            )
