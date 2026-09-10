"""Базовые классы для компонентов бота: доступ к боту и проверка прав на команды."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from twitchio.ext import commands

if TYPE_CHECKING:
    from twitch_bot.core.bot import TwitchBot

__all__ = ["AccessDeniedError", "OwnerOnlyComponent", "PublicComponent", "TwitchComponent"]


class AccessDeniedError(Exception):
    """Бросается из `component_before_invoke`, когда команду вызвали там, где не положено."""

    def __init__(self, message: str, *, silent: bool = False) -> None:
        """Создать ошибку отказа в доступе.

        Parameters
        ----------
        message : str
            Текст, который увидит пользователь в чате — если только не выставлен ``silent``.
        silent : bool, default=False
            Если True, обработчик ошибок команд (`TwitchBot.event_command_error`)
            промолчит в чат вместо того, чтобы объяснять отказ.
        """
        super().__init__(message)
        self.silent = silent


class TwitchComponent(commands.Component):
    """Общий предок всех компонентов: просто хранит ссылку на бота, которому принадлежит."""

    def __init__(self, bot: TwitchBot) -> None:
        """Привязать компонент к боту, в который он будет загружен.

        Parameters
        ----------
        bot : TwitchBot
            Экземпляр бота — через него компонент достаёт всё остальное
            (пул БД, ID владельца и так далее).
        """
        self.bot = bot


class PublicComponent(TwitchComponent):
    """От этого класса наследуются команды и листенеры, доступные на любом авторизованном канале."""


class OwnerOnlyComponent(TwitchComponent):
    """Компоненты-наследники доступны только в канале владельца бота, остальным — отказ."""

    @override
    async def component_before_invoke(self, ctx: commands.Context[Any]) -> None:
        """Проверить перед вызовом команды, что это действительно канал владельца.

        Raises
        ------
        AccessDeniedError
            Если команда пришла из любого канала, кроме владельца.
        """
        if ctx.broadcaster.id != self.bot.owner_id:
            raise AccessDeniedError("Эта команда доступна только в канале владельца.", silent=True)
