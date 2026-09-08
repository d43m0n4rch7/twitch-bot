# Contributing to twitch-bot

Thanks for your interest in contributing. This project is still focused on
**structure and infrastructure**; real product features are built on top of the
existing component, EventSub, and database layers.

By participating, you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## Requirements

- **Python 3.12 only** (`requires-python = ">=3.12,<3.13"`)
- [uv](https://github.com/astral-sh/uv)
- PostgreSQL (for anything that touches the database)
- Optional: [Just](https://github.com/casey/just)

## Setup

```bash
just sync
cp .env.example .env
# fill TWITCH_*, DATABASE_URL, EVENTSUB_SECRET, OAUTH_DOMAIN
just migrate
just run-scopes   # authorize bot / owner / public when needed
just run
```

See [README.md](../README.md) for layout, migrations, and deploy overview.

## Development workflow

1. Fork and create a branch from `main`.
2. Make your changes.
3. Run the full quality gate before opening a PR:

```bash
just pre-commit-install   # once per clone
just check                # lint + format-check + typecheck + test
```

Or individually: `just lint`, `just typecheck`, `just test`.

4. Open a pull request against `main` with a short description of **what** and **why**.

### Style and tooling

- **Ruff** for lint and format (`target-version = py312`)
- **Pyright** for types
- **Pre-commit** hooks should pass on the whole tree
- Prefer typed public APIs and docstrings consistent with existing modules

## Project conventions

### Components (commands & listeners)

1. Add a module under `src/twitch_bot/components/`.
2. Subclass `PublicComponent` or `OwnerOnlyComponent`.
3. Export `async def setup(bot) -> None` and call `await bot.add_component(...)`.
4. Register the module path in `COMPONENT_MODULES` in
   `src/twitch_bot/components/__init__.py`.

Details and examples: [README — Adding a component](../README.md#adding-a-component).

### EventSub subscriptions

- Public set: `build_public_subscriptions` in `src/twitch_bot/core/eventsub.py`
- Owner set: `build_owner_subscriptions` (includes the public set)
- Combined at startup via `build_subscriptions` (owner + active public channels from the DB)

To add a new event type: extend the appropriate builder, handle it in a
component listener, then restart with `--force-subscribe` so the conduit
recreates subscriptions.

Details: [README — Adding EventSub subscriptions](../README.md#adding-eventsub-subscriptions).

### Database

- Models and CRUD live under `src/database/`
- Schema changes go through **Alembic** (`just migrate`, revision via
  `uv run alembic revision --autogenerate -m "..."`)
- Do not hand-edit production schema outside migrations

### Tests

Foundation coverage already exists (config, models, session URLs, CRUD,
EventSub builders, component access guards). When you add behavior:

- Prefer unit tests next to the same concern (helpers, guards, builders)
- No live Twitch API or e2e tests are required for small changes
- Run with `just test`

## Issues

- **Bugs** and **feature ideas** — use the GitHub issue forms only
  (blank issues are disabled).
- Search existing issues before opening a new one.
- Keep proposals concrete and scoped; vague “make it better” requests are hard
  to act on.

## Pull requests

- Keep PRs focused (one concern per PR when practical).
- `just check` must pass.
- Do not commit secrets, real tokens, or production `.env` files.
- License of contributions is **MPL-2.0** (same as the project).

## Questions

Use [GitHub Discussions](https://github.com/d43m0n4rch7/twitch-bot/discussions)
for questions that are not ready as bugs or feature requests.
