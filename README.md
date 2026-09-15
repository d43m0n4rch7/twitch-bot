# Twitch Bot

Production-oriented Twitch bot on **TwitchIO 3** (`commands.AutoBot`) with **SQLAlchemy 2** (async + asyncpg), **Alembic**, **PostgreSQL**, and a component architecture.

## Features

- OAuth for bot, owner, and public channels; tokens stored in PostgreSQL
- EventSub: extended set for the owner channel, basic set for public channels
- Hot-reloadable command/listener components
- Full ORM + CRUD layer; Alembic migrations applied on startup
- SSH deploy to a VPS on push to `main` (systemd + Caddy)

## Why asyncpg and psycopg?

| Package | Role |
|---------|------|
| **asyncpg** | Async SQLAlchemy engine (`postgresql+asyncpg://`) at runtime |
| **psycopg** | Sync driver for Alembic migrations (`postgresql+psycopg://`) |

## Layout

```
src/database/        SQLAlchemy models, sessions, CRUD, migrations
src/twitch_bot/
  main.py
  core/
    bot.py, config.py, eventsub.py
    database/    models, session, migrations, CRUD
    base/        components and context
  components/    commands and listeners
tests/
alembic/
deploy/
```

## Requirements

- Python 3.12+
- PostgreSQL
- [uv](https://github.com/astral-sh/uv)
- Optional: [Just](https://github.com/casey/just)

## Setup

```bash
just sync
cp .env.example .env
# fill TWITCH_*, DATABASE_URL, EVENTSUB_SECRET, OAUTH_DOMAIN
just migrate
just run-scopes   # authorize bot / owner / public
just run
```

## Quality

```bash
just test
just lint
just typecheck
just check                 # lint + format-check + typecheck + test
just pre-commit-install    # once per clone
just pre-commit-run        # all hooks on the whole tree
```

## Migrations

```bash
just migrate
just migrate-down
uv run alembic revision --autogenerate -m "description"
```

## Deploy

Push to `main`. The workflow SSHs to the server, resets to `origin/main`, runs `uv sync --no-dev --frozen`, and restarts `twitch-bot.service`. See `DEPLOYMENT.md`.

## CI

Pull requests and pushes to `main` run lint, format check, typecheck, and tests via `.github/workflows/ci.yml`.

## Community

- Contributing: [`.github/CONTRIBUTING.md`](.github/CONTRIBUTING.md)
- Code of Conduct: [`.github/CODE_OF_CONDUCT.md`](.github/CODE_OF_CONDUCT.md)
- Security: [`.github/SECURITY.md`](.github/SECURITY.md)

## License

Mozilla Public License 2.0 — see `LICENSE`.
