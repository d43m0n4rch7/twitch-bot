"""Сам класс бота: наследник TwitchIO AutoBot, который хранит OAuth в PostgreSQL и умеет EventSub."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, override

import twitchio
from twitchio.ext import commands
from twitchio.web import StarletteAdapter

from twitch_bot.components import COMPONENT_MODULES
from twitch_bot.core.base.component import AccessDeniedError
from twitch_bot.core.base.context import TwitchContext
from twitch_bot.core.database import delete_token, load_tokens, save_token, upsert_channel
from twitch_bot.core.eventsub import build_owner_subscriptions, build_public_subscriptions

if TYPE_CHECKING:
    import asyncpg
    from twitchio import eventsub

logger = logging.getLogger(__name__)

LOCAL_DOMAIN = "http://localhost:4343"

# Скоупы для самого аккаунта бота — без них он не сможет ни читать, ни писать в чат.
BOT_SCOPES: list[str] = [
    "user:read:chat",
    "user:write:chat",
    "user:bot",
    "moderator:read:followers",
]

# Скоупы для канала владельца. Их набор шире, чем у обычных каналов, —
# именно они дают доступ к расширенным подпискам EventSub из
# eventsub.build_owner_subscriptions (фоллоу, рейды, редемпшены и т.д.).
OWNER_SCOPES: list[str] = [
    "channel:bot",
    "channel:moderate",
    "channel:read:redemptions",
    "channel:manage:redemptions",
    "channel:read:subscriptions",
    "moderator:read:followers",
]

# Минимальный скоуп для любого стороннего канала, который просто разрешил боту чатиться у себя.
PUBLIC_SCOPES: list[str] = ["channel:bot"]


class TwitchBot(commands.AutoBot):
    """Главный класс бота: токены в PostgreSQL, подписки EventSub, компоненты по требованию."""

    if TYPE_CHECKING:
        bot_id: str  # pyright: ignore[reportIncompatibleMethodOverride]
        owner_id: str  # pyright: ignore[reportIncompatibleMethodOverride]

    def __init__(
        self,
        *,
        pool: asyncpg.Pool,
        client_id: str,
        client_secret: str,
        bot_id: str,
        owner_id: str,
        command_prefix: str,
        subscriptions: list[eventsub.SubscriptionPayload],
        eventsub_secret: str,
        oauth_domain: str,
        scopes_only: bool = False,
        force_subscribe: bool = False,
        local: bool = False,
    ) -> None:
        """Собрать бота и выбрать, какой адаптер будет принимать OAuth/EventSub-запросы.

        Parameters
        ----------
        pool : asyncpg.Pool
            Пул PostgreSQL, через который бот читает и пишет OAuth-токены.
        client_id, client_secret : str
            Credentials приложения из Twitch Developer Console.
        bot_id, owner_id : str
            Twitch user ID аккаунта бота и канала его владельца.
        command_prefix : str
            Префикс текстовых команд в чате (например, ``"!"``).
        subscriptions : list of twitchio.eventsub.SubscriptionPayload
            Подписки EventSub, с которыми Conduit бота поднимется при старте.
        eventsub_secret : str
            Секрет, которым подписаны webhook-запросы EventSub — используется для их проверки.
        oauth_domain : str
            Публичный HTTPS-домен, на который Twitch будет слать OAuth- и EventSub-callback'и.
        scopes_only : bool, default=False
            Если True, компоненты не загружаются — бот только печатает ссылки для OAuth и ждёт.
        force_subscribe : bool, default=False
            Пересоздать начальные подписки EventSub на Conduit, даже если они уже есть.
        local : bool, default=False
            Поднять локальный HTTP-адаптер на ``http://localhost:4343`` вместо
            публичного Starlette-адаптера — удобно для отладки без реального домена.
        """
        self.pool = pool
        self.scopes_only = scopes_only
        self.domain = (LOCAL_DOMAIN if local else oauth_domain).rstrip("/")

        adapter: StarletteAdapter[Any] | None = (
            None if local else StarletteAdapter(host="0.0.0.0", domain=self.domain, eventsub_secret=eventsub_secret)
        )

        super().__init__(
            client_id=client_id,
            client_secret=client_secret,
            bot_id=bot_id,
            owner_id=owner_id,
            prefix=command_prefix,
            subscriptions=subscriptions,
            force_subscribe=force_subscribe,
            adapter=adapter,  # pyright: ignore[reportArgumentType]
        )

    # -- жизненный цикл ---------------------------------------------------

    @override
    async def setup_hook(self) -> None:
        """Загрузить компоненты сразу после того, как TwitchIO закончит аутентификацию.

        В режиме scopes-only компоненты не трогаем вообще — вместо этого
        просто печатаем ссылки OAuth в лог и ждём, пока их кто-то откроет.
        """
        if self.scopes_only:
            logger.warning("Режим scopes-only. Откройте эти URL для авторизации:\n%s", self.oauth_links())
            return
        for module in COMPONENT_MODULES:
            await self.load_module(module)

    async def event_ready(self) -> None:
        """Отметить в логе, что бот успешно залогинился и готов работать."""
        logger.info("Вошли как Twitch-бот %s", self.bot_id)

    # -- OAuth --------------------------------------------------------------

    def oauth_link(self, scopes: list[str]) -> str:
        """Построить ссылку на OAuth-авторизацию для текущего адаптера (локального или публичного).

        Parameters
        ----------
        scopes : list of str
            Скоупы, которые нужно запросить у пользователя.

        Returns
        -------
        str
            Готовая ссылка — открываете её в браузере и авторизуете приложение.
        """
        return f"{self.domain}/oauth?scopes={'+'.join(scopes)}&force_verify=true"

    def oauth_links(self) -> str:
        """Собрать сразу три ссылки: для бота, для владельца и для произвольного публичного канала."""
        return "\n".join(
            (
                f"BOT:    {self.oauth_link(BOT_SCOPES)}",
                f"OWNER:  {self.oauth_link(OWNER_SCOPES)}",
                f"PUBLIC: {self.oauth_link(PUBLIC_SCOPES)}",
            )
        )

    @override
    async def event_oauth_authorized(self, payload: twitchio.authentication.UserTokenPayload) -> None:
        """Обработать успешную OAuth-авторизацию: сохранить токен и подписать канал на EventSub.

        Срабатывает каждый раз, когда кто-то проходит по ссылке из
        `oauth_link` и подтверждает доступ. Токен самого бота сюда тоже
        залетает, но подписки для него не нужны — выходим сразу.

        Parameters
        ----------
        payload : twitchio.authentication.UserTokenPayload
            Данные, которые адаптер вернул по завершении OAuth-flow.
        """
        await self.add_token(payload.access_token, payload.refresh_token)
        if not payload.user_id or payload.user_id == self.bot_id:
            return

        subscriptions = (
            build_owner_subscriptions(self.owner_id, self.bot_id)
            if payload.user_id == self.owner_id
            else build_public_subscriptions(payload.user_id, self.bot_id)
        )
        response = await self.multi_subscribe(subscriptions)
        if response.errors:
            logger.warning("Не удалось подписаться для пользователя %s: %s", payload.user_id, response.errors)

    async def add_token(self, token: str, refresh: str) -> twitchio.authentication.ValidateTokenPayload:
        """Передать пару токенов в TwitchIO, а заодно сохранить их и владельца в PostgreSQL.

        Помимо самих токенов, апсертит канал в `twitch_channels`, определяя
        его тип (bot / owner / public) по совпадению user ID.

        Parameters
        ----------
        token, refresh : str
            Access- и refresh-токен пользователя.

        Returns
        -------
        twitchio.authentication.ValidateTokenPayload
            Результат валидации токена, который вернул сам Twitch.
        """
        validated = await super().add_token(token, refresh)
        if not validated.user_id:
            raise RuntimeError("Twitch вернул токен без user ID")

        await save_token(self.pool, validated.user_id, token, refresh, scopes=validated.scopes)

        users = await self.fetch_users(ids=[validated.user_id])
        user = users[0] if users else None
        channel_type = (
            "bot" if validated.user_id == self.bot_id else "owner" if validated.user_id == self.owner_id else "public"
        )
        await upsert_channel(
            self.pool,
            validated.user_id,
            channel_type,
            login=user.name if user else validated.login,
            display_name=user.display_name if user else validated.login,
        )
        logger.info("Сохранён токен для пользователя Twitch %s (%s)", validated.user_id, channel_type)
        return validated

    @override
    async def load_tokens(self, _: str | None = None) -> None:
        """Подтянуть OAuth-токены из PostgreSQL — вместо файла, который использует TwitchIO по умолчанию.

        Если какой-то сохранённый токен уже невалиден (например, его
        отозвали на стороне Twitch), просто удаляем его из базы и идём
        дальше — падать из-за одного протухшего токена смысла нет.
        """
        for token, refresh in await load_tokens(self.pool):
            try:
                await self.add_token(token, refresh)
            except twitchio.InvalidTokenException as error:
                logger.warning("Удаляю невалидный токен при старте: %s", error)
                if error.token:
                    await delete_token(self.pool, error.token)

    async def event_token_refreshed(self, payload: twitchio.TokenRefreshedPayload) -> None:
        """Сохранить обновлённую пару токенов сразу же, как только TwitchIO её обновит."""
        await save_token(self.pool, payload.user_id, payload.token, payload.refresh_token, scopes=payload.scopes)
        logger.info("Сохранён обновлённый токен для пользователя Twitch %s", payload.user_id)

    # -- команды и контекст -------------------------------------------------

    @override
    async def event_command_error(self, payload: commands.CommandErrorPayload) -> None:
        """Разобрать ошибку команды: ожидаемые случаи — ответом в чат, неожиданные — в лог.

        Порядок проверок важен: сначала разворачиваем `CommandInvokeError`
        до исходного исключения, а дальше идём по известным типам ошибок
        сверху вниз. Всё, что не подошло ни под один случай, считается
        неожиданным и летит в лог с полным traceback.

        Parameters
        ----------
        payload : twitchio.ext.commands.CommandErrorPayload
            Контекст вызова и само исключение, которые прислал TwitchIO.
        """
        error = payload.exception
        if isinstance(error, commands.CommandInvokeError) and error.original:
            error = error.original

        if isinstance(error, AccessDeniedError):
            if not error.silent:
                await payload.context.reply(str(error))
            return
        if isinstance(error, commands.CommandNotFound):
            logger.debug("Неизвестная команда: %s", payload.context.invoked_with)
            return
        if isinstance(error, commands.CommandOnCooldown):
            await payload.context.reply(f"Команда на кулдауне ещё {error.remaining:.0f} с.")
            return
        if isinstance(error, commands.MissingRequiredArgument):
            await payload.context.reply(f'Нужно указать "{error.param.name}".')
            return
        if isinstance(error, twitchio.HTTPException):
            logger.error("Ошибка Twitch API при обработке команды: %s", error, exc_info=error)
            await payload.context.reply("Twitch отклонил этот запрос.")
            return

        logger.error("Неожиданная ошибка команды: %s", error, exc_info=error)
        await payload.context.reply("Что-то пошло не так при выполнении команды.")

    @override
    async def event_error(self, payload: twitchio.EventErrorPayload) -> None:
        """Поймать и залогировать всё, что вылетело из листенера необработанным."""
        logger.error("Необработанная ошибка листенера: %s", payload.error, exc_info=payload.error)

    @override
    def get_context(
        self,
        payload: twitchio.ChatMessage | twitchio.ChannelPointsRedemptionAdd | twitchio.ChannelPointsRedemptionUpdate,
        *,
        cls: Any = None,
    ) -> TwitchContext:
        """Подставить `TwitchContext` вместо стандартного контекста TwitchIO для любой команды."""
        return super().get_context(payload, cls=cls or TwitchContext)
