"""Tests for owner-only component access control."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from twitch_bot.core.base.component import AccessDeniedError, OwnerOnlyComponent


class _OwnerOnly(OwnerOnlyComponent):
    pass


@pytest.mark.asyncio
async def test_owner_only_allows_owner_channel() -> None:
    bot = SimpleNamespace(owner_id="owner-1")
    component = _OwnerOnly(bot)  # type: ignore[arg-type]
    ctx = SimpleNamespace(broadcaster=SimpleNamespace(id="owner-1"))
    await component.component_before_invoke(ctx)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_owner_only_rejects_foreign_channel() -> None:
    bot = SimpleNamespace(owner_id="owner-1")
    component = _OwnerOnly(bot)  # type: ignore[arg-type]
    ctx = SimpleNamespace(broadcaster=SimpleNamespace(id="other"))
    with pytest.raises(AccessDeniedError) as exc_info:
        await component.component_before_invoke(ctx)  # type: ignore[arg-type]
    assert exc_info.value.silent is True


def test_access_denied_error_defaults() -> None:
    error = AccessDeniedError("no")
    assert str(error) == "no"
    assert error.silent is False
    silent = AccessDeniedError("no", silent=True)
    assert silent.silent is True
