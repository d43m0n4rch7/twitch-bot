"""Basic example chat commands."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

import twitchio
from twitchio.ext import commands

from twitch_bot.core.base.component import OwnerOnlyComponent, PublicComponent

if TYPE_CHECKING:
    from twitch_bot.core.base.context import TwitchContext
    from twitch_bot.core.bot import TwitchBot


class BasicCommands(PublicComponent):
    """Commands available in any authorized channel."""

    @commands.command()
    async def ping(self, ctx: TwitchContext) -> None:
        """Reply with a health-check response.

        Parameters
        ----------
        ctx : TwitchContext
            Invocation context.

        Notes
        -----
        Usage: ``!ping``
        """
        await ctx.reply("Pong!")

    @commands.command()
    async def hi(self, ctx: TwitchContext) -> None:
        """Greet the invoking chatter.

        Parameters
        ----------
        ctx : TwitchContext
            Invocation context.

        Notes
        -----
        Usage: ``!hi``
        """
        await ctx.reply(f"Hi, {ctx.chatter}!")

    @commands.command()
    async def choice(self, ctx: TwitchContext, *choices: str) -> None:
        """Randomly pick one of the given choices.

        Parameters
        ----------
        ctx : TwitchContext
            Invocation context.
        *choices : str
            Candidate strings provided by the chatter.

        Notes
        -----
        Usage: ``!choice <choice_1> <choice_2> ...``
        """
        if not choices:
            await ctx.reply("Give me at least one choice.")
            return
        await ctx.reply(f"I choose: {random.choice(choices)}")

    @commands.group(invoke_fallback=True)
    async def socials(self, ctx: TwitchContext) -> None:
        """Group command that lists social links.

        Parameters
        ----------
        ctx : TwitchContext
            Invocation context.

        Notes
        -----
        Usage: ``!socials``
        """
        await ctx.reply("discord.gg/..., youtube.com/..., twitch.tv/...")

    @socials.command(name="discord")
    async def socials_discord(self, ctx: TwitchContext) -> None:
        """Send only the Discord invite.

        Parameters
        ----------
        ctx : TwitchContext
            Invocation context.

        Notes
        -----
        Usage: ``!socials discord``
        """
        await ctx.reply("discord.gg/...")


class OwnerCommands(OwnerOnlyComponent):
    """Commands restricted to the owner's own channel."""

    @commands.command()
    async def shoutout(self, ctx: TwitchContext, user: twitchio.User) -> None:
        """Give another streamer a shoutout.

        Parameters
        ----------
        ctx : TwitchContext
            Invocation context.
        user : twitchio.User
            Target user resolved by TwitchIO converters.

        Notes
        -----
        Usage: ``!shoutout <user>``
        """
        await ctx.reply(f"Go check out {user.mention}, they were last playing something great!")


async def setup(bot: TwitchBot) -> None:
    """Register basic and owner command components.

    Parameters
    ----------
    bot : TwitchBot
        Application bot that receives the components.
    """
    await bot.add_component(BasicCommands(bot))
    await bot.add_component(OwnerCommands(bot))
