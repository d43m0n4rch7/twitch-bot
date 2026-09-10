# Twitch Bot

Twitch-бот на базе TwitchIO 3 (`commands.AutoBot`), PostgreSQL и EventSub.

## Что умеет

- Авторизует аккаунт бота, канал владельца и любые другие каналы через Twitch OAuth и сохраняет токены в PostgreSQL, чтобы они переживали перезапуски.
- Подписывается на события EventSub: расширенный набор для канала владельца (фолловы, подписки, рейды, редемпшены channel points, баны, обновления канала) и базовый набор для остальных авторизованных каналов (сообщения чата, стрим online/offline).
- Запускает чат-команды и листенеры событий через систему компонентов — фичи можно добавлять и перезагружать отдельными модулями.
- Применяет схему БД автоматически при старте.
- Деплоится на VPS по SSH при каждом пуше в `main` и работает за Caddy, чтобы запросы OAuth/EventSub от Twitch доходили по HTTPS без туннелей.

## Что внутри

- `src/twitch_bot/main.py` — точка входа CLI (argparse): `--local`, `--scopes-only`, `--force-subscribe`, `--log-level`.
- `src/twitch_bot/core/` — ядро:
  - `config.py` — настройки из переменных окружения / `.env`.
  - `database.py` — пул PostgreSQL, схема, хранение токенов и каналов.
  - `bot.py` — класс `TwitchBot`: OAuth-ссылки, сохранение токенов, подписка на EventSub при авторизации, обработка ошибок команд.
  - `eventsub.py` — сборка списков подписок EventSub.
- `src/twitch_bot/core/base/` — общие базовые классы:
  - `context.py` — кастомный контекст команд.
  - `component.py` — базовые классы компонентов (`PublicComponent`, `OwnerOnlyComponent`) и ошибка отказа в доступе.
- `src/twitch_bot/components/` — сами команды и листенеры, каждый модуль можно hot-reload'ить:
  - `basic.py` — примеры команд (`!ping`, `!hi`, `!choice`, `!socials`, `!shoutout`).
  - `events.py` — листенеры EventSub (follow, subscribe, raid, points redemption, stream online/offline).
- `.env.example` — шаблон переменных окружения.
- `.pre-commit-config.yaml` — хуки pre-commit (Ruff lint + format).
- `migrations/001_init.sql` — таблицы `twitch_tokens` и `twitch_channels`.
- `Justfile` — шорткаты для частых команд (`just run-twitch`, `just lint`, `just format`, ...); `just` покажет список.
- `deploy/twitch-bot.service` — unit systemd для запуска бота на VPS.
- `deploy/Caddyfile` — конфиг reverse proxy, отдающий порт OAuth/EventSub бота по HTTPS.
- `.github/workflows/deploy.yml` — линтит код и деплоит на VPS по SSH при пуше в `main`.

## Стек

Python 3.14+, TwitchIO 3, asyncpg, pydantic-settings, uv, Just.

## Запуск

```bash
just sync
cp .env.example .env
just run-twitch-scopes   # получить OAuth-ссылки (локальный адаптер)
just run-twitch
```

Без `just` то же самое: `uv sync` и `uv run twitch-bot [флаги]`.


## Pre-commit

Перед коммитом автоматически гоняются Ruff (lint + format).

```bash
just sync
just pre-commit-install   # один раз: поставить git-хуки
just pre-commit           # прогнать на всём репозитории
```

Без `just`: `uv run pre-commit install` и `uv run pre-commit run --all-files`.
Конфиг — `.pre-commit-config.yaml`.

## Деплой

См. `DEPLOYMENT.md` — настройка VPS, Caddy, systemd-сервиса и автодеплоя при пуше.
