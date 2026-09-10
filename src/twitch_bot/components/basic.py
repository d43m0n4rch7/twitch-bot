"""Простой набор команд для примера — берите как отправную точку и переделывайте под себя."""

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
    """Простые команды, которые работают на любом канале, куда авторизован бот."""

    @commands.command()
    async def ping(self, ctx: TwitchContext) -> None:
        """Проверить, что бот жив и отвечает.

        !ping
        """
        await ctx.reply("Понг!")

    @commands.command()
    async def hi(self, ctx: TwitchContext) -> None:
        """Поздороваться с тем, кто написал команду.

        !hi
        """
        await ctx.reply(f"Привет, {ctx.chatter}!")

    @commands.command()
    async def choice(self, ctx: TwitchContext, *choices: str) -> None:
        """Подкинуть монетку между несколькими вариантами и выбрать один.

        !choice <вариант_1> <вариант_2> ...
        """
        if not choices:
            await ctx.reply("Дай хотя бы один вариант.")
            return
        await ctx.reply(f"Выбираю: {random.choice(choices)}")

    @commands.group(invoke_fallback=True)
    async def socials(self, ctx: TwitchContext) -> None:
        """Показать ссылки на все соцсети сразу.

        !socials
        """
        await ctx.reply("discord.gg/..., youtube.com/..., twitch.tv/...")

    @socials.command(name="discord")
    async def socials_discord(self, ctx: TwitchContext) -> None:
        """Показать только ссылку на Discord, без остального списка.

        !socials discord
        """
        await ctx.reply("discord.gg/...")


class OwnerCommands(OwnerOnlyComponent):
    """Команды, которые имеют смысл только на канале владельца бота."""

    @commands.command()
    async def shoutout(self, ctx: TwitchContext, user: twitchio.User) -> None:
        """Похвалить другого стримера и оставить ссылку на его канал.

        !shoutout <пользователь>
        """
        await ctx.reply(f"Загляните к {user.mention}, у них крутой контент!")


async def setup(bot: TwitchBot) -> None:
    """Подключить к боту команды из этого модуля — точка входа, которую дёргает `load_module`.

    Parameters
    ----------
    bot : TwitchBot
        Бот, к которому добавляются компоненты `BasicCommands` и `OwnerCommands`.
    """
    await bot.add_component(BasicCommands(bot))
    await bot.add_component(OwnerCommands(bot))
