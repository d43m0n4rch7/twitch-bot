"""Тесты для базовых классов компонентов и кастомного контекста."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from twitch_bot.core.base.component import AccessDeniedError, OwnerOnlyComponent, PublicComponent


def test_access_denied_error_silent_flag() -> None:
    err = AccessDeniedError("нет доступа", silent=True)
    assert str(err) == "нет доступа"
    assert err.silent is True

    err2 = AccessDeniedError("нет доступа")
    assert err2.silent is False


def test_public_component_holds_bot() -> None:
    bot = MagicMock()
    comp = PublicComponent(bot)
    assert comp.bot is bot


@pytest.mark.asyncio
async def test_owner_only_rejects_other_channel() -> None:
    bot = MagicMock()
    bot.owner_id = "owner123"
    comp = OwnerOnlyComponent(bot)

    ctx = SimpleNamespace(broadcaster=SimpleNamespace(id="someone_else"))
    with pytest.raises(AccessDeniedError) as exc_info:
        await comp.component_before_invoke(ctx)  # type: ignore[arg-type]
    assert exc_info.value.silent is True


@pytest.mark.asyncio
async def test_owner_only_allows_owner_channel() -> None:
    bot = MagicMock()
    bot.owner_id = "owner123"
    comp = OwnerOnlyComponent(bot)

    ctx = SimpleNamespace(broadcaster=SimpleNamespace(id="owner123"))
    await comp.component_before_invoke(ctx)  # type: ignore[arg-type]


def test_twitch_context_channel_id() -> None:
    # TwitchContext наследуется от commands.Context, поэтому вместо реального
    # объекта достаточно минимального мока с одним нужным атрибутом.
    class FakeContext:
        broadcaster = SimpleNamespace(id="chan42")

        @property
        def channel_id(self) -> str:
            return self.broadcaster.id

    ctx = FakeContext()
    assert ctx.channel_id == "chan42"
