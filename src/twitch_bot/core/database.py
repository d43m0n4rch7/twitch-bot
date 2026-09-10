"""Всё, что бот знает о PostgreSQL: пул подключений, миграции и хранение токенов/каналов."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import asyncpg

if TYPE_CHECKING:
    from collections.abc import Iterable

__all__ = [
    "apply_schema",
    "create_pool",
    "delete_token",
    "load_public_user_ids",
    "load_tokens",
    "save_token",
    "upsert_channel",
]

_MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "migrations"


async def create_pool(database_url: str) -> asyncpg.Pool:
    """Поднять пул асинхронных подключений к PostgreSQL.

    Parameters
    ----------
    database_url : str
        Строка подключения к PostgreSQL (подойдёт, например, connection string из Supabase).

    Returns
    -------
    asyncpg.Pool
        Готовый к работе пул, который дальше передаётся во все функции этого модуля.
    """
    return await asyncpg.create_pool(
        database_url,
        command_timeout=60,
        min_size=1,
        max_size=10,
        # Supabase гоняет соединения через Supavisor (transaction pooler),
        # а он не умеет prepared statements — поэтому кэш statements в
        # asyncpg приходится выключать, иначе запросы начнут падать.
        statement_cache_size=0,
    )


async def apply_schema(pool: asyncpg.Pool) -> None:
    """Прогнать все `migrations/*.sql` по очереди, в алфавитном порядке имён файлов.

    Специальной таблицы с версиями миграций тут нет — вместо неё каждый файл
    написан через `create table if not exists` и подобные идемпотентные
    конструкции. Поэтому схему можно спокойно накатывать при каждом старте
    бота, не думая о том, применялась она уже или нет.

    Parameters
    ----------
    pool : asyncpg.Pool
        Открытый пул подключений к PostgreSQL.
    """
    async with pool.acquire() as connection:
        for path in sorted(_MIGRATIONS_DIR.glob("*.sql")):
            await connection.execute(path.read_text(encoding="utf-8"))


async def load_tokens(pool: asyncpg.Pool) -> list[tuple[str, str]]:
    """Забрать из базы все сохранённые пары access/refresh-токенов Twitch.

    Используется при старте бота вместо стандартной загрузки токенов
    TwitchIO из файла — см. `TwitchBot.load_tokens`.

    Returns
    -------
    list of tuple of str
        Пары ``(access_token, refresh_token)`` для каждого авторизованного пользователя.
    """
    rows = await pool.fetch("select access_token, refresh_token from twitch_tokens order by user_id")
    return [(row["access_token"], row["refresh_token"]) for row in rows]


async def load_public_user_ids(pool: asyncpg.Pool, *, exclude: Iterable[str] = ()) -> list[str]:
    """Найти ID всех активных каналов, у которых есть сохранённые credentials.

    Нужно, чтобы при старте пересобрать подписки EventSub для каналов,
    которые авторизовали бота ранее (не считая самого бота и владельца —
    для них подписки строятся отдельно).

    Parameters
    ----------
    pool : asyncpg.Pool
        Открытый пул подключений к PostgreSQL.
    exclude : iterable of str, default=()
        ID пользователей, которых нужно выкинуть из результата
        (обычно это ID бота и владельца).

    Returns
    -------
    list of str
        Twitch user ID каналов, оставшихся после исключения.
    """
    rows = await pool.fetch("select user_id from twitch_channels where is_active = true order by user_id")
    excluded = set(exclude)
    return [row["user_id"] for row in rows if row["user_id"] not in excluded]


async def save_token(
    pool: asyncpg.Pool,
    user_id: str,
    access_token: str,
    refresh_token: str,
    *,
    scopes: Iterable[str] = (),
) -> None:
    """Сохранить пару токенов пользователя: вставить новую строку или обновить существующую.

    Parameters
    ----------
    pool : asyncpg.Pool
        Открытый пул подключений к PostgreSQL.
    user_id : str
        Twitch user ID, которому принадлежат эти токены.
    access_token : str
        Актуальный access-токен.
    refresh_token : str
        Актуальный refresh-токен.
    scopes : iterable of str, default=()
        Скоупы, которые Twitch выдал этому токену.
    """
    await pool.execute(
        """
        insert into twitch_tokens (user_id, access_token, refresh_token, scopes, updated_at)
        values ($1, $2, $3, $4, now())
        on conflict (user_id) do update set
            access_token = excluded.access_token,
            refresh_token = excluded.refresh_token,
            scopes = excluded.scopes,
            updated_at = now()
        """,
        user_id,
        access_token,
        refresh_token,
        list(scopes),
    )


async def upsert_channel(
    pool: asyncpg.Pool,
    user_id: str,
    channel_type: str,
    *,
    login: str | None = None,
    display_name: str | None = None,
) -> None:
    """Завести канал в базе или обновить его, если он уже был авторизован ранее.

    Заодно помечает канал активным (`is_active = true`) — так что повторная
    авторизация канала, который раньше отключал бота, снова включит его
    в список рабочих подписок.

    Parameters
    ----------
    pool : asyncpg.Pool
        Открытый пул подключений к PostgreSQL.
    user_id : str
        Twitch user ID канала.
    channel_type : str
        Роль канала: ``"owner"``, ``"bot"`` или ``"public"``.
    login : str, optional
        Логин пользователя в Twitch.
    display_name : str, optional
        Отображаемое имя пользователя в Twitch.
    """
    await pool.execute(
        """
        insert into twitch_channels (user_id, login, display_name, channel_type)
        values ($1, $2, $3, $4)
        on conflict (user_id) do update set
            login = excluded.login,
            display_name = excluded.display_name,
            channel_type = excluded.channel_type,
            is_active = true,
            updated_at = now()
        """,
        user_id,
        login,
        display_name,
        channel_type,
    )


async def delete_token(pool: asyncpg.Pool, access_token: str) -> None:
    """Удалить токен, который Twitch перестал считать валидным.

    Вызывается при старте бота, когда очередной сохранённый токен не
    проходит валидацию — незачем хранить в базе то, чем всё равно не
    получится воспользоваться.

    Parameters
    ----------
    pool : asyncpg.Pool
        Открытый пул подключений к PostgreSQL.
    access_token : str
        Невалидный access-токен, по которому ищем нужную строку в БД.
    """
    await pool.execute("delete from twitch_tokens where access_token = $1", access_token)
