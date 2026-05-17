"""Command-line entry point for the Twitch bot process."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

import colorlog

from twitch_bot.core.bot import TwitchBot
from twitch_bot.core.config import get_settings, require
from database import Database, run_migrations
from database.crud import channels as channels_crud
from twitch_bot.core.eventsub import build_subscriptions

logger = logging.getLogger(__name__)


def configure_logging(level: str) -> None:
    """Configure root logging with colorlog on stderr.

    Parameters
    ----------
    level : str
        Logging level name (for example ``INFO`` or ``DEBUG``).

    Notes
    -----
    Existing root handlers are replaced so a previous basicConfig or library
    setup cannot leave plain formatters in place.
    """
    handler = colorlog.StreamHandler(stream=sys.stderr)
    handler.setFormatter(
        colorlog.ColoredFormatter(
            fmt="%(asctime)s %(log_color)s[%(levelname)s]%(reset)s %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            },
            secondary_log_colors={},
            style="%",
        )
    )

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())


async def run(*, scopes_only: bool, force_subscribe: bool, local: bool) -> None:
    """Create resources and run the bot until it is closed.

    Parameters
    ----------
    scopes_only : bool
        Skip component loading and only print OAuth links.
    force_subscribe : bool
        Recreate the initial EventSub subscriptions on the conduit.
    local : bool
        Use the local HTTP OAuth/EventSub adapter instead of the public domain.
    """
    settings = get_settings()
    require(
        settings,
        "twitch_client_id",
        "twitch_client_secret",
        "twitch_bot_id",
        "twitch_owner_id",
        "eventsub_secret",
    )
    assert settings.twitch_client_id is not None
    assert settings.twitch_client_secret is not None
    assert settings.twitch_bot_id is not None
    assert settings.twitch_owner_id is not None
    assert settings.eventsub_secret is not None

    run_migrations(settings.database_url)

    database = Database(settings.database_url)
    try:
        async with database.session() as session:
            public_user_ids = await channels_crud.list_active_user_ids(
                session,
                exclude=(settings.twitch_bot_id, settings.twitch_owner_id),
            )

        subscriptions = build_subscriptions(
            settings.twitch_owner_id,
            settings.twitch_bot_id,
            public_user_ids,
        )

        bot = TwitchBot(
            database=database,
            client_id=settings.twitch_client_id,
            client_secret=settings.twitch_client_secret,
            bot_id=settings.twitch_bot_id,
            owner_id=settings.twitch_owner_id,
            subscriptions=subscriptions,
            eventsub_secret=settings.eventsub_secret,
            oauth_domain=settings.oauth_domain,
            scopes_only=scopes_only,
            force_subscribe=force_subscribe,
            local=local,
        )
        try:
            await bot.start(load_tokens=True, save_tokens=False)
        finally:
            await bot.close()
    finally:
        await database.close()


def main() -> int:
    """Parse command-line arguments and start the bot.

    Returns
    -------
    int
        Process exit code (``0`` on success, ``1`` on startup failure).
    """
    parser = argparse.ArgumentParser(description="Run the Twitch bot.")
    parser.add_argument(
        "--scopes-only",
        action="store_true",
        help="Print OAuth authorization links and skip loading components.",
    )
    parser.add_argument(
        "--force-subscribe",
        "-f",
        action="store_true",
        help="Recreate initial EventSub subscriptions on the Conduit.",
    )
    parser.add_argument(
        "--local",
        "-l",
        action="store_true",
        help="Use the local HTTP adapter at http://localhost:4343 instead of OAUTH_DOMAIN.",
    )
    parser.add_argument(
        "--log-level",
        default=None,
        help="Override LOG_LEVEL from the environment (e.g. DEBUG).",
    )
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(args.log_level or settings.log_level)

    try:
        asyncio.run(run(scopes_only=args.scopes_only, force_subscribe=args.force_subscribe, local=args.local))
    except (RuntimeError, ValueError) as error:
        logger.error("Startup failed: %s", error)
        return 1
    except KeyboardInterrupt:
        logger.info("Shutting down")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
