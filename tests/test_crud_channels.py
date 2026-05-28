"""Unit tests for channel CRUD helpers using a mocked session."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from database.crud import channels as channels_crud


@pytest.mark.asyncio
async def test_list_active_user_ids_applies_exclude() -> None:
    ch1 = MagicMock(user_id="1")
    ch2 = MagicMock(user_id="2")
    result = MagicMock()
    result.scalars.return_value.all.return_value = [ch1, ch2]
    session = AsyncMock()
    session.execute.return_value = result

    ids = await channels_crud.list_active_user_ids(session, exclude=("1",))
    assert ids == ["2"]


@pytest.mark.asyncio
async def test_deactivate_calls_set_active() -> None:
    result = MagicMock()
    result.rowcount = 1
    session = AsyncMock()
    session.execute.return_value = result

    assert await channels_crud.deactivate(session, "user-1") is True
    session.execute.assert_awaited()
