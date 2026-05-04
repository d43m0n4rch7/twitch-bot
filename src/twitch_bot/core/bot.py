"""TwitchIO AutoBot subclass with SQLAlchemy-backed OAuth and EventSub."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, override

import twitchio
from twitchio.ext import commands
from twitchio.web import StarletteAdapter

from twitch_bot.components import COMPONENT_MODULES
from twitch_bot.core.base.component import AccessDeniedError
from twitch_bot.core.base.context import TwitchContext
from database.crud import channels as channels_crud, tokens as tokens_crud
from database.models import ChannelType
from twitch_bot.core.eventsub import build_owner_subscriptions, build_public_subscriptions

if TYPE_CHECKING:
    from twitchio import eventsub

    from database.session import Database

logger = logging.getLogger(__name__)

LOCAL_DOMAIN = "http://localhost:4343"
BOT_SCOPES: list[str] = [
    "user:read:chat",
    "user:write:chat",
    "user:bot",
    "moderator:read:followers",
]

OWNER_SCOPES: list[str] = [
    "channel:bot",
    "channel:moderate",
    "channel:read:redemptions",
    "channel:manage:redemptions",
    "channel:read:subscriptions",
    "moderator:read:followers",
]

PUBLIC_SCOPES: list[str] = ["channel:bot"]


class TwitchBot(commands.AutoBot):
    """Application bot with PostgreSQL token storage, EventSub and components.

    Parameters
    ----------
    database : Database
        SQLAlchemy database handle used for token and channel persistence.
    client_id : str
        Twitch application client ID.
    client_secret : str
        Twitch application client secret.
    bot_id : str
        Twitch user ID of the bot account.
    owner_id : str
        Twitch user ID of the owner channel.
    subscriptions : list of eventsub.SubscriptionPayload
        Initial EventSub subscriptions assigned to the bot conduit.
    eventsub_secret : str
        Secret used to validate EventSub webhook requests. Must be stable across restarts.
    oauth_domain : str
        Public HTTPS domain that receives OAuth and EventSub callbacks in production.
    scopes_only : bool, default False
        Skip component loading and only print OAuth links on startup.
    force_subscribe : bool, default False
        Recreate the initial EventSub subscriptions on the conduit.
    local : bool, default False
        Bind the web adapter for local development (no public domain).
    """

    if TYPE_CHECKING:
        bot_id: str  # pyright: ignore[reportIncompatibleMethodOverride]
        owner_id: str  # pyright: ignore[reportIncompatibleMethodOverride]

    def __init__(
        self,
        *,
        database: Database,
        client_id: str,
        client_secret: str,
        bot_id: str,
        owner_id: str,
        subscriptions: list[eventsub.SubscriptionPayload],
        eventsub_secret: str,
        oauth_domain: str,
        scopes_only: bool = False,
        force_subscribe: bool = False,
        local: bool = False,
    ) -> None:
        self.database = database
        self.scopes_only = scopes_only
        self.local = local
        self.domain = (LOCAL_DOMAIN if local else oauth_domain).rstrip("/")

        adapter: StarletteAdapter[Any] | None = (
            None
            if local
            else StarletteAdapter(
                host="0.0.0.0",  # noqa: S104
                domain=self.domain,
                eventsub_secret=eventsub_secret,
            )
        )

        super().__init__(
            client_id=client_id,
            client_secret=client_secret,
            bot_id=bot_id,
            owner_id=owner_id,
            prefix="!",
            subscriptions=subscriptions,
            force_subscribe=force_subscribe,
            adapter=adapter,  # pyright: ignore[reportArgumentType]
        )

    @override
    async def setup_hook(self) -> None:
        """Load feature components after authentication unless scopes-only mode."""
        if self.scopes_only:
            logger.warning("Scopes-only mode. Open these URLs to authorize:\n%s", self.oauth_links())
            return
        for module in COMPONENT_MODULES:
            await self.load_module(module)

    async def event_ready(self) -> None:
        """Log successful login of the bot account."""
        logger.info("Logged in as Twitch bot %s", self.bot_id)

    def oauth_link(self, scopes: list[str]) -> str:
        """Build an OAuth authorization URL for the configured adapter domain.

        Parameters
        ----------
        scopes : list of str
            Requested Twitch OAuth scopes.

        Returns
        -------
        str
            Browser URL that starts the authorization flow.
        """
        base = self.domain if not self.local else LOCAL_DOMAIN
        return f"{base}/oauth?scopes={'+'.join(scopes)}&force_verify=true"

    def oauth_links(self) -> str:
        """Return multi-line authorization links for bot, owner and public tiers.

        Returns
        -------
        str
            Formatted block with three OAuth URLs.
        """
        return "\n".join(
            (
                f"BOT:    {self.oauth_link(BOT_SCOPES)}",
                f"OWNER:  {self.oauth_link(OWNER_SCOPES)}",
                f"PUBLIC: {self.oauth_link(PUBLIC_SCOPES)}",
            )
        )

    @override
    async def event_oauth_authorized(self, payload: twitchio.authentication.UserTokenPayload) -> None:
        """Persist a newly authorized token and subscribe its EventSub events.

        Parameters
        ----------
        payload : twitchio.authentication.UserTokenPayload
            OAuth payload returned after a successful authorization flow.
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
            logger.warning("Failed to subscribe for user %s: %s", payload.user_id, response.errors)

    @override
    async def add_token(self, token: str, refresh: str) -> twitchio.authentication.ValidateTokenPayload:
        """Register a token with TwitchIO and persist it through the CRUD layer.

        Parameters
        ----------
        token : str
            Twitch user access token.
        refresh : str
            Twitch refresh token.

        Returns
        -------
        twitchio.authentication.ValidateTokenPayload
            Validation payload returned by Twitch.

        Raises
        ------
        RuntimeError
            If Twitch validates the token without a user ID.
        """
        validated = await super().add_token(token, refresh)
        if not validated.user_id:
            raise RuntimeError("Twitch returned a token without a user ID")

        if validated.user_id == self.bot_id:
            channel_type = ChannelType.bot
        elif validated.user_id == self.owner_id:
            channel_type = ChannelType.owner
        else:
            channel_type = ChannelType.public

        users = await self.fetch_users(ids=[validated.user_id])
        user = users[0] if users else None
        login = user.name if user else validated.login
        display_name = user.display_name if user else validated.login

        async with self.database.session() as session:
            await tokens_crud.upsert(
                session,
                user_id=validated.user_id,
                access_token=token,
                refresh_token=refresh,
                scopes=validated.scopes or (),
            )
            await channels_crud.upsert(
                session,
                user_id=validated.user_id,
                channel_type=channel_type,
                login=login,
                display_name=display_name,
            )

        logger.info("Stored token for Twitch user %s (%s)", validated.user_id, channel_type.value)
        return validated

    @override
    async def load_tokens(self, _: str | None = None) -> None:
        """Load OAuth tokens from PostgreSQL instead of TwitchIO's token file.

        Parameters
        ----------
        _ : str or None, optional
            Ignored path argument kept for TwitchIO API compatibility.
        """
        async with self.database.session() as session:
            pairs = await tokens_crud.list_token_pairs(session)

        for token, refresh in pairs:
            try:
                await self.add_token(token, refresh)
            except twitchio.InvalidTokenException as error:
                logger.warning("Removing invalid token during startup: %s", error)
                if error.token:
                    async with self.database.session() as session:
                        await tokens_crud.delete_by_access_token(session, error.token)

    async def event_token_refreshed(self, payload: twitchio.TokenRefreshedPayload) -> None:
        """Persist a token pair after TwitchIO refreshes it.

        Parameters
        ----------
        payload : twitchio.TokenRefreshedPayload
            Refresh event dispatched by TwitchIO.
        """
        async with self.database.session() as session:
            await tokens_crud.upsert(
                session,
                user_id=payload.user_id,
                access_token=payload.token,
                refresh_token=payload.refresh_token,
                scopes=payload.scopes or (),
            )
        logger.info("Stored refreshed token for Twitch user %s", payload.user_id)

    @override
    async def event_command_error(self, payload: commands.CommandErrorPayload) -> None:
        """Handle expected command errors and log unexpected failures.

        Parameters
        ----------
        payload : commands.CommandErrorPayload
            Command context and exception dispatched by TwitchIO.
        """
        error = payload.exception
        if isinstance(error, commands.CommandInvokeError) and error.original:
            error = error.original

        if isinstance(error, AccessDeniedError):
            if not error.silent:
                await payload.context.reply(str(error))
            return
        if isinstance(error, commands.CommandNotFound):
            logger.debug("Unknown command: %s", payload.context.invoked_with)
            return
        if isinstance(error, commands.CommandOnCooldown):
            await payload.context.reply(f"That command is on cooldown for another {error.remaining:.0f}s.")
            return
        if isinstance(error, commands.MissingRequiredArgument):
            await payload.context.reply(f'You need to provide "{error.param.name}".')
            return
        if isinstance(error, twitchio.HTTPException):
            logger.error("Twitch API error handling command: %s", error, exc_info=error)
            await payload.context.reply("Twitch rejected that request.")
            return

        logger.error("Unexpected command failure: %s", error, exc_info=error)
        await payload.context.reply("Something went wrong while running that command.")

    @override
    async def event_error(self, payload: twitchio.EventErrorPayload) -> None:
        """Log unhandled errors raised inside listeners.

        Parameters
        ----------
        payload : twitchio.EventErrorPayload
            Error payload from the event dispatcher.
        """
        logger.error("Unhandled listener error: %s", payload.error, exc_info=payload.error)

    @override
    def get_context(
        self,
        payload: twitchio.ChatMessage | twitchio.ChannelPointsRedemptionAdd | twitchio.ChannelPointsRedemptionUpdate,
        *,
        cls: Any = None,
    ) -> TwitchContext:
        """Create the application command context for a message or redemption.

        Parameters
        ----------
        payload : ChatMessage or ChannelPointsRedemptionAdd or ChannelPointsRedemptionUpdate
            Incoming Twitch event used to build the context.
        cls : type, optional
            Optional context class override; defaults to :class:`TwitchContext`.

        Returns
        -------
        TwitchContext
            Context instance used by command handlers.
        """
        return super().get_context(payload, cls=cls or TwitchContext)
