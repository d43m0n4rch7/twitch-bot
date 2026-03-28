"""Environment-backed application configuration."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or a ``.env`` file.

    Attributes
    ----------
    twitch_client_id : str
        Twitch application client ID.
    twitch_client_secret : str
        Twitch application client secret.
    twitch_bot_id : str
        Twitch user ID of the bot account.
    twitch_owner_id : str
        Twitch user ID of the owner channel.
    database_url : str
        PostgreSQL connection URI.
    eventsub_secret : str
        Secret used to validate EventSub webhook signatures.
    oauth_domain : str
        Public HTTPS base URL for OAuth and EventSub callbacks.
    log_level : str
        Default logging level name (for example ``INFO`` or ``DEBUG``).
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    twitch_client_id: str = Field(min_length=1)
    twitch_client_secret: str = Field(min_length=1)
    twitch_bot_id: str = Field(min_length=1)
    twitch_owner_id: str = Field(min_length=1)

    database_url: str = Field(min_length=1)

    eventsub_secret: str = Field(min_length=16)
    oauth_domain: str = "http://localhost:4343"

    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings instance.

    Returns
    -------
    Settings
        Settings loaded from the process environment and optional ``.env`` file.
    """
    return Settings()  # pyright: ignore[reportCallIssue]


def require(settings: Settings, *names: str) -> None:
    """Fail fast if any of the named settings are unset.

    Parameters
    ----------
    settings : Settings
        Settings instance to check.
    *names : str
        Attribute names that must be truthy.

    Raises
    ------
    RuntimeError
        If any of the named settings are ``None`` or empty.
    """
    missing = [name for name in names if not getattr(settings, name, None)]
    if missing:
        raise RuntimeError(f"Missing required settings: {', '.join(missing)}")
