# Как контрибьютить

Спасибо за интерес к проекту! Это краткий гайд о том, как настроить
окружение, что проверяется в CI и как оформить изменения, чтобы их
было проще смержить.

Прежде чем начать — ознакомьтесь с [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Требования

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) — для управления зависимостями и venv
- Доступ к PostgreSQL (локально, в Docker или, например, бесплатный
  проект в Supabase) — бот без базы не запустится
- Приложение в [Twitch Developer Console](https://dev.twitch.tv/console),
  если планируете гонять бота живьём, а не только тесты

## Настройка окружения

```bash
git clone https://github.com/d43m0n4rch7/twitch-bot.git
cd twitch-bot

just sync              # поставит зависимости по uv.lock, включая dev-группу
just pre-commit-install # поставит git-хуки pre-commit
cp .env.example .env   # заполните своими значениями
```

Все доступные команды — `just --list` или сразу заглянуть в [Justfile](Justfile).

## Локальный запуск бота

Для разработки удобнее всего запускать бота с локальным HTTP-адаптером
(не нужен публичный домен и HTTPS):

```bash
just run-twitch-local
```

Чтобы сначала просто получить ссылки OAuth-авторизации, не поднимая
компоненты:

```bash
just run-twitch-scopes
```

## Прежде чем открыть PR

Прогоните весь набор локальных проверок — это ровно то, что запускает CI:

```bash
just check
```

Это эквивалент `lint + format-check + typecheck + test`. Отдельные шаги:

```bash
just lint          # ruff check .
just format        # ruff check . --fix && ruff format .
just format-check   # ruff format --check .
just typecheck      # pyright (строгий режим)
just test            # pytest -q
```

Если pre-commit установлен (`just pre-commit-install`), часть этих
проверок и так отработает автоматически при коммите.

## Стиль кода

- Форматирование и линт — [Ruff](https://docs.astral.sh/ruff/), настройки
  в `pyproject.toml` (`line-length = 120`, двойные кавычки, py314).
- Аннотации типов обязательны для публичного кода — `pyright` работает в
  `typeCheckingMode = "strict"`. Тесты (`tests/**/*.py`) от этого
  освобождены (`per-file-ignores`).
- Docstring'и — в стиле **NumPy** (`convention = "numpy"` в
  `[tool.ruff.lint.pydocstyle]`). Пишите их так, будто объясняете код
  живому человеку: что делает функция и, если не очевидно, почему
  именно так — а не просто повторяете сигнатуру словами.
- Импорты сортирует `ruff` (`isort`-совместимый блок), запускайте
  `just format` перед коммитом, а не разбирайтесь руками.

## Тесты

- Юнит-тесты лежат в `tests/`, запускаются через `pytest` (`asyncio_mode
  = "auto"`, так что `async def test_...` работает без лишних декораторов).
- Для нового поведения — будь то команда, листенер EventSub или функция
  в `core/` — добавляйте тест рядом с уже существующими, по аналогии с
  `tests/test_component.py` и `tests/test_eventsub.py`.
- Тестам не нужны реальный Twitch и PostgreSQL — используются `MagicMock`
  и `SimpleNamespace` вместо реальных объектов TwitchIO.

## Коммиты и PR

- Коммиты — в духе [Conventional Commits](https://www.conventionalcommits.org/):
  `feat(...)`, `fix(...)`, `docs(...)`, `test(...)`, `chore(...)`,
  `ci(...)`. Название — кратко и по делу, тело коммита (по желанию) —
  что и зачем изменилось.
- Один PR — одна логическая единица изменений. Не смешивайте рефактор
  с новой фичей.
- Убедитесь, что `just check` проходит локально — CI (`.github/workflows/ci.yml`)
  прогоняет ровно те же шаги на каждый push и PR в `main`.
- В описании PR коротко опишите, что изменилось и почему. Если правите
  баг — как его воспроизвести.

## Структура проекта, если нужно ориентироваться

```
src/twitch_bot/
├── core/            # настройки, БД, EventSub-подписки, класс TwitchBot
│   └── base/        # базовые классы компонентов и кастомный контекст
├── components/       # команды и листенеры, подключаемые к боту
└── main.py           # точка входа CLI
```

Новый компонент с командами или листенерами добавляйте в
`src/twitch_bot/components/` и регистрируйте его модуль в
`COMPONENT_MODULES` (`src/twitch_bot/components/__init__.py`).

## Вопросы

Если что-то не понятно или не запускается — заводите issue, лучше с
шаблоном [bug report](.github/ISSUE_TEMPLATE/bug-report.md) или
[feature request](.github/ISSUE_TEMPLATE/feature-request.md), смотря
что подходит.
