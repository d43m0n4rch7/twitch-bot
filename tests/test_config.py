"""Тесты для config.py: проверяем require() на «всё есть» и «чего-то не хватает»."""

from __future__ import annotations

import pytest

from twitch_bot.core.config import Settings, require


def test_require_passes_when_all_set() -> None:
    settings = Settings(
        database_url="postgresql://user:pass@localhost/db",
        twitch_client_id="id",
        twitch_client_secret="secret",
        twitch_bot_id="bot",
        twitch_owner_id="owner",
        eventsub_secret="secret",
    )
    require(settings, "twitch_client_id", "twitch_bot_id")


def test_require_raises_on_missing() -> None:
    settings = Settings(database_url="postgresql://user:pass@localhost/db")
    with pytest.raises(RuntimeError, match="Не заданы обязательные настройки"):
        require(settings, "twitch_client_id", "twitch_bot_id")
