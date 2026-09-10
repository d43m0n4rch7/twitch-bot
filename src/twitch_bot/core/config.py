"""Настройки бота: читаем их из переменных окружения или файла `.env`."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["Settings", "get_settings", "require"]


class Settings(BaseSettings):
    """Все настройки бота в одном месте: подхватываются из окружения, а локально можно держать в `.env`."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(min_length=1)
    log_level: str = "INFO"

    twitch_client_id: str | None = None
    twitch_client_secret: str | None = None
    twitch_bot_id: str | None = None
    twitch_owner_id: str | None = None
    eventsub_secret: str | None = None
    oauth_domain: str = "http://localhost:4343"
    twitch_command_prefix: str = "!"


@lru_cache
def get_settings() -> Settings:
    """Отдать настройки приложения, читая окружение только один раз за всё время работы.

    Обёрнута в `lru_cache`, чтобы `Settings()` не парсился заново на каждый вызов —
    доступ к настройкам возможен из любого модуля без протаскивания объекта через все функции.

    Returns
    -------
    Settings
        Настройки, собранные из переменных окружения и, если он есть, файла `.env`.
    """
    return Settings()  # pyright: ignore[reportCallIssue]


def require(settings: Settings, *names: str) -> None:
    """Проверить, что перечисленные настройки заданы, и упасть с понятной ошибкой, если нет.

    Удобно вызвать один раз в начале `main()`, чтобы не гоняться потом за
    `AttributeError` или `None` где-то в глубине кода бота.

    Parameters
    ----------
    settings : Settings
        Объект настроек, который нужно проверить.
    *names : str
        Имена полей, которые обязательно должны быть заполнены (непусты).

    Raises
    ------
    RuntimeError
        Если хотя бы одно из перечисленных полей равно `None` или пустой строке.
    """
    missing = [name for name in names if not getattr(settings, name, None)]
    if missing:
        raise RuntimeError(f"Не заданы обязательные настройки: {', '.join(missing)}")
