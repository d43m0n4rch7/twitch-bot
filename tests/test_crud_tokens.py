"""Unit tests for token CRUD helpers using a mocked session."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from database.crud import tokens as tokens_crud


@pytest.mark.asyncio
async def test_list_token_pairs_maps_rows() -> None:
    row1 = SimpleNamespace(access_token="a1", refresh_token="r1")
    row2 = SimpleNamespace(access_token="a2", refresh_token="r2")
    result = MagicMock()
    result.all.return_value = [row1, row2]
    session = AsyncMock()
    session.execute.return_value = result

    pairs = await tokens_crud.list_token_pairs(session)
    assert pairs == [("a1", "r1"), ("a2", "r2")]
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_by_access_token_returns_bool() -> None:
    result = MagicMock()
    result.rowcount = 1
    session = AsyncMock()
    session.execute.return_value = result

    assert await tokens_crud.delete_by_access_token(session, "tok") is True

    result.rowcount = 0
    assert await tokens_crud.delete_by_access_token(session, "missing") is False
