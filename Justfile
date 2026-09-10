set shell := ["bash", "-uc"]

# Показать доступные команды.
default:
    @just --list

# Установить зависимости по lock-файлу.
sync:
    uv sync

# Обновить зависимости до последних допустимых версий.
update:
    uv lock --upgrade
    uv sync

# Запустить Twitch-бота.
run-twitch:
    uv run twitch-bot

# Запустить бота с локальным HTTP-адаптером OAuth/EventSub (публичный домен не нужен).
run-twitch-local:
    uv run twitch-bot --local

# Вывести OAuth-ссылки Twitch без загрузки компонентов.
run-twitch-scopes:
    uv run twitch-bot --scopes-only

# Пересоздать начальные подписки EventSub на Conduit.
run-twitch-force:
    uv run twitch-bot --force-subscribe

# Установить git-хуки pre-commit.
pre-commit-install:
    uv run pre-commit install

# Прогнать pre-commit на всех файлах.
pre-commit:
    uv run pre-commit run --all-files

# Прогнать проверки Ruff.
lint:
    uv run ruff check .

# Исправить линт и отформатировать проект.
format:
    uv run ruff check . --fix
    uv run ruff format .

# Проверить форматирование без изменений файлов.
format-check:
    uv run ruff format --check .

# Строгая проверка типов.
typecheck:
    uv run pyright

# Запустить unit-тесты.
test:
    uv run pytest -q

# Все локальные проверки качества.
check: lint format-check typecheck test
