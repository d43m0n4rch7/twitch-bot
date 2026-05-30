"""Tests for EventSub subscription builders."""

from __future__ import annotations

from twitch_bot.core.eventsub import (
    build_owner_subscriptions,
    build_public_subscriptions,
    build_subscriptions,
)


def test_build_public_subscriptions_count() -> None:
    subs = build_public_subscriptions("broadcaster", "bot")
    assert len(subs) == 3


def test_build_owner_subscriptions_includes_public() -> None:
    public = build_public_subscriptions("owner", "bot")
    owner = build_owner_subscriptions("owner", "bot")
    # public set (3) + follow, raid, subscribe, subscribe_message, points, update, ban (7)
    assert len(owner) == len(public) + 7


def test_build_subscriptions_deduplicates_owner_and_bot() -> None:
    subs = build_subscriptions("owner", "bot", ["owner", "bot", "public1", "public1"])
    public_only = build_subscriptions("owner", "bot", ["public1"])
    assert len(subs) == len(public_only)
    assert len(subs) == len(build_owner_subscriptions("owner", "bot")) + 3


def test_build_subscriptions_empty_public() -> None:
    subs = build_subscriptions("owner", "bot", [])
    assert len(subs) == len(build_owner_subscriptions("owner", "bot"))
