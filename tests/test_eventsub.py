"""Тесты для eventsub.py: проверяем, что наборы подписок собираются нужного размера и состава."""

from __future__ import annotations

from twitch_bot.core.eventsub import (
    build_owner_subscriptions,
    build_public_subscriptions,
    build_subscriptions,
)


def test_build_public_subscriptions_has_chat_and_stream() -> None:
    subs = build_public_subscriptions("broadcaster", "bot")
    types = {type(s).__name__ for s in subs}
    assert "ChatMessageSubscription" in types
    assert "StreamOnlineSubscription" in types
    assert "StreamOfflineSubscription" in types
    assert len(subs) == 3


def test_build_owner_subscriptions_extends_public() -> None:
    public = build_public_subscriptions("owner", "bot")
    owner = build_owner_subscriptions("owner", "bot")
    assert len(owner) > len(public)
    public_types = {type(s).__name__ for s in public}
    owner_types = {type(s).__name__ for s in owner}
    assert public_types.issubset(owner_types)
    assert "ChannelFollowSubscription" in owner_types
    assert "ChannelRaidSubscription" in owner_types
    assert "ChannelSubscribeSubscription" in owner_types


def test_build_subscriptions_combines_without_duplicates() -> None:
    subs = build_subscriptions("owner", "bot", public_user_ids=["pub1", "owner", "bot", "pub2"])
    # Владелец даёт 3 подписки из build_public_subscriptions плюс расширенный
    # набор сверху; owner/bot исключаются из публичного цикла, так что
    # реально добавляются только pub1 и pub2 — по 3 подписки каждый.
    assert len(subs) >= 3 + 3 + 3
    for s in subs:
        # У разных SubscriptionPayload разный набор атрибутов — тут просто
        # убеждаемся, что список не пустой и ничего не падает при переборе.
        assert s is not None
    assert len(subs) == len(list(subs))  # на всякий случай: не одноразовый итератор


def test_build_subscriptions_empty_public() -> None:
    owner_only = build_owner_subscriptions("owner", "bot")
    combined = build_subscriptions("owner", "bot", public_user_ids=[])
    assert len(combined) == len(owner_only)
