"""Tests for application settings loading."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from twitch_bot.core.config import Settings, get_settings, require


def _clear_twitch_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "TWITCH_CLIENT_ID",
        "TWITCH_CLIENT_SECRET",
        "TWITCH_BOT_ID",
        "TWITCH_OWNER_ID",
        "DATABASE_URL",
        "EVENTSUB_SECRET",
        "OAUTH_DOMAIN",
        "LOG_LEVEL",
    ):
        monkeypatch.delenv(key, raising=False)


def test_settings_requires_credentials(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Missing env and no .env file must fail validation."""
    get_settings.cache_clear()
    _clear_twitch_env(monkeypatch)
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValidationError):
        Settings()  # pyright: ignore[reportCallIssue]


def test_settings_loads_from_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    get_settings.cache_clear()
    _clear_twitch_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TWITCH_CLIENT_ID", "cid")
    monkeypatch.setenv("TWITCH_CLIENT_SECRET", "csecret")
    monkeypatch.setenv("TWITCH_BOT_ID", "bot")
    monkeypatch.setenv("TWITCH_OWNER_ID", "owner")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost/db")
    monkeypatch.setenv("EVENTSUB_SECRET", "secret-secret-16")
    monkeypatch.setenv("OAUTH_DOMAIN", "https://oauth.example.com")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    settings = Settings()  # pyright: ignore[reportCallIssue]
    assert settings.twitch_client_id == "cid"
    assert settings.twitch_bot_id == "bot"
    assert settings.log_level == "DEBUG"
    assert settings.oauth_domain == "https://oauth.example.com"
    get_settings.cache_clear()


def test_require_raises_on_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    get_settings.cache_clear()
    _clear_twitch_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TWITCH_CLIENT_ID", "cid")
    monkeypatch.setenv("TWITCH_CLIENT_SECRET", "csecret")
    monkeypatch.setenv("TWITCH_BOT_ID", "bot")
    monkeypatch.setenv("TWITCH_OWNER_ID", "owner")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost/db")
    monkeypatch.setenv("EVENTSUB_SECRET", "secret-secret-16")

    settings = Settings()  # pyright: ignore[reportCallIssue]
    broken = settings.model_copy(update={"twitch_client_id": ""})
    with pytest.raises(RuntimeError, match="Missing required settings"):
        require(broken, "twitch_client_id")
    get_settings.cache_clear()
