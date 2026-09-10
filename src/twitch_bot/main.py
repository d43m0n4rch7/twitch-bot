"""Точка входа: собирает настройки, БД и бота, разбирает аргументы CLI."""

from __future__ import annotations

import argparse
import asyncio
import logging

from twitch_bot.core.bot import TwitchBot
from twitch_bot.core.config import get_settings, require
from twitch_bot.core.database import apply_schema, create_pool, load_public_user_ids
from twitch_bot.core.eventsub import build_subscriptions

logger = logging.getLogger(__name__)


async def run(*, scopes_only: bool, force_subscribe: bool, local: bool) -> None:
    """Поднять пул БД, накатить схему, собрать бота и держать его запущенным до остановки.

    Всё, что здесь создаётся (пул подключений, сам бот), аккуратно
    закрывается в `finally`, даже если что-то упадёт по пути — чтобы не
    оставлять висящие соединения с PostgreSQL.

    Parameters
    ----------
    scopes_only : bool
        Не грузить компоненты, а только напечатать ссылки для OAuth и выйти.
    force_subscribe : bool
        Пересоздать начальные подписки EventSub на Conduit, даже если они уже есть.
    local : bool
        Поднять локальный HTTP-адаптер вместо публичного домена из настроек.
    """
    settings = get_settings()
    require(settings, "twitch_client_id", "twitch_client_secret", "twitch_bot_id", "twitch_owner_id", "eventsub_secret")
    assert settings.twitch_client_id is not None
    assert settings.twitch_client_secret is not None
    assert settings.twitch_bot_id is not None
    assert settings.twitch_owner_id is not None
    assert settings.eventsub_secret is not None

    pool = await create_pool(settings.database_url)
    try:
        await apply_schema(pool)

        public_user_ids = await load_public_user_ids(
            pool,
            exclude=(settings.twitch_bot_id, settings.twitch_owner_id),
        )
        subscriptions = build_subscriptions(settings.twitch_owner_id, settings.twitch_bot_id, public_user_ids)

        bot = TwitchBot(
            pool=pool,
            client_id=settings.twitch_client_id,
            client_secret=settings.twitch_client_secret,
            bot_id=settings.twitch_bot_id,
            owner_id=settings.twitch_owner_id,
            command_prefix=settings.twitch_command_prefix,
            subscriptions=subscriptions,
            eventsub_secret=settings.eventsub_secret,
            oauth_domain=settings.oauth_domain,
            scopes_only=scopes_only,
            force_subscribe=force_subscribe,
            local=local,
        )
        try:
            # TwitchBot сам сохраняет токены в PostgreSQL — в add_token и
            # event_token_refreshed. Стандартный plaintext-файл TwitchIO тут
            # только продублировал бы секреты на диске, поэтому save_tokens=False.
            await bot.start(load_tokens=True, save_tokens=False)
        finally:
            await bot.close()
    finally:
        await pool.close()


def main() -> int:
    """Разобрать аргументы командной строки, настроить логирование и запустить бота."""
    parser = argparse.ArgumentParser(description="Запуск Twitch-бота.")
    parser.add_argument(
        "--scopes-only",
        action="store_true",
        help="Не загружать компоненты, а только вывести ссылки OAuth.",
    )
    parser.add_argument(
        "--force-subscribe",
        "-f",
        action="store_true",
        help="Пересоздать начальные подписки EventSub на Conduit.",
    )
    parser.add_argument(
        "--local",
        "-l",
        action="store_true",
        help="Запустить локальный HTTP-адаптер на http://localhost:4343 вместо OAUTH_DOMAIN.",
    )
    parser.add_argument(
        "--log-level",
        default=None,
        help="Переопределить LOG_LEVEL из окружения (например, DEBUG).",
    )
    args = parser.parse_args()

    settings = get_settings()
    logging.basicConfig(
        level=args.log_level or settings.log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    try:
        asyncio.run(run(scopes_only=args.scopes_only, force_subscribe=args.force_subscribe, local=args.local))
    except (RuntimeError, ValueError) as error:
        logger.error("Ошибка запуска: %s", error)
        return 1
    except KeyboardInterrupt:
        logger.info("Остановка")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
