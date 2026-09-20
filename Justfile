set shell := ["bash", "-uc"]

# List available recipes.
default:
    @just --list

# Install project dependencies with uv (including dev group).
sync:
    uv sync

# Upgrade lockfile to latest allowed versions and re-sync.
update:
    uv lock --upgrade
    uv sync

# Run the bot (production-style entrypoint).
run:
    uv run twitch-bot

# Run the bot with the local HTTP adapter (no public OAUTH_DOMAIN).
run-local:
    uv run twitch-bot --local

# Print OAuth authorization links without loading components.
run-scopes:
    uv run twitch-bot --scopes-only --local

# Recreate initial EventSub subscriptions on the Conduit.
run-force:
    uv run twitch-bot --force-subscribe

# Apply Alembic migrations up to head.
migrate:
    uv run alembic upgrade head

# Roll back one Alembic migration.
migrate-down:
    uv run alembic downgrade -1

# Show Alembic migration history.
migrate-history:
    uv run alembic history

# Run the test suite.
test:
    uv run pytest

# Run the test suite quietly.
test-cov:
    uv run pytest -q

# Run Ruff lint checks.
lint:
    uv run ruff check .

# Apply Ruff fixes and format the codebase.
format:
    uv run ruff check . --fix
    uv run ruff format .

# Check formatting without writing changes.
format-check:
    uv run ruff format --check .

# Run Pyright type checking.
typecheck:
    uv run pyright

# Install git pre-commit hooks for this repository.
pre-commit-install:
    uv run pre-commit install

# Run all pre-commit hooks against the entire tree.
pre-commit-run:
    uv run pre-commit run --all-files

# Update hook revisions in .pre-commit-config.yaml to the latest tags.
pre-commit-update:
    uv run pre-commit autoupdate

# Uninstall git pre-commit hooks from this repository.
pre-commit-uninstall:
    uv run pre-commit uninstall

# Run lint, format check, typecheck, and tests.
check: lint format-check typecheck test

