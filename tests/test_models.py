"""Tests for ORM enums and model metadata."""

from __future__ import annotations

import pytest

from database.models import ChannelType, TwitchChannel, TwitchToken


def test_channel_type_values() -> None:
    assert ChannelType.owner.value == "owner"
    assert ChannelType.bot.value == "bot"
    assert ChannelType.public.value == "public"


def test_channel_type_from_str() -> None:
    assert ChannelType("public") is ChannelType.public
    with pytest.raises(ValueError):
        ChannelType("invalid")


def test_table_names() -> None:
    assert TwitchToken.__tablename__ == "twitch_tokens"
    assert TwitchChannel.__tablename__ == "twitch_channels"
