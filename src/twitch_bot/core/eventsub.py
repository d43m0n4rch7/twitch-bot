"""Собираем наборы подписок EventSub для разных типов каналов."""

from __future__ import annotations

from typing import TYPE_CHECKING

from twitchio import eventsub

if TYPE_CHECKING:
    from collections.abc import Iterable

__all__ = ["build_owner_subscriptions", "build_public_subscriptions", "build_subscriptions"]


def build_public_subscriptions(broadcaster_id: str, bot_id: str) -> list[eventsub.SubscriptionPayload]:
    """Собрать минимальный набор подписок для стороннего канала, который просто пригласил бота.

    Такой канал дал боту только скоуп `channel:bot`, поэтому ему доступны
    только сообщения чата и статус стрима — без модераторских и
    владельческих событий из `build_owner_subscriptions`.

    Parameters
    ----------
    broadcaster_id : str
        Twitch user ID канала, для которого собираем подписки.
    bot_id : str
        Twitch user ID самого бота — он же получатель событий чата.

    Returns
    -------
    list of twitchio.eventsub.SubscriptionPayload
        Три подписки: сообщения чата, начало и конец стрима.
    """
    return [
        eventsub.ChatMessageSubscription(broadcaster_user_id=broadcaster_id, user_id=bot_id),
        eventsub.StreamOnlineSubscription(broadcaster_user_id=broadcaster_id),
        eventsub.StreamOfflineSubscription(broadcaster_user_id=broadcaster_id),
    ]


def build_owner_subscriptions(owner_id: str, bot_id: str) -> list[eventsub.SubscriptionPayload]:
    """Собрать полный набор подписок для родного канала бота — того, кому принадлежат OWNER_SCOPES.

    Дополняет базовый набор из `build_public_subscriptions` событиями,
    которые имеют смысл только на главном канале: фоллоу, рейды, подписки,
    редемпшены баллов, изменения канала и баны.

    Parameters
    ----------
    owner_id : str
        Twitch user ID канала владельца.
    bot_id : str
        Twitch user ID бота.

    Returns
    -------
    list of twitchio.eventsub.SubscriptionPayload
        Публичные подписки плюс расширенный набор владельческих событий.
    """
    return [
        *build_public_subscriptions(owner_id, bot_id),
        eventsub.ChannelFollowSubscription(broadcaster_user_id=owner_id, moderator_user_id=bot_id),
        eventsub.ChannelRaidSubscription(to_broadcaster_user_id=owner_id),
        eventsub.ChannelSubscribeSubscription(broadcaster_user_id=owner_id),
        eventsub.ChannelSubscribeMessageSubscription(broadcaster_user_id=owner_id),
        eventsub.ChannelPointsRedeemAddSubscription(broadcaster_user_id=owner_id),
        eventsub.ChannelUpdateSubscription(broadcaster_user_id=owner_id),
        eventsub.ChannelBanSubscription(broadcaster_user_id=owner_id),
    ]


def build_subscriptions(
    owner_id: str, bot_id: str, public_user_ids: Iterable[str]
) -> list[eventsub.SubscriptionPayload]:
    """Собрать разом все подписки, с которыми бот должен подняться при старте.

    Каналу владельца достаётся расширенный набор, всем остальным ранее
    авторизованным каналам — публичный. Если среди `public_user_ids`
    случайно затесались ID владельца или бота, они молча пропускаются,
    чтобы не задваивать подписки.

    Parameters
    ----------
    owner_id : str
        Twitch user ID канала владельца.
    bot_id : str
        Twitch user ID бота.
    public_user_ids : iterable of str
        Twitch user ID остальных каналов, которые уже авторизовали бота.

    Returns
    -------
    list of twitchio.eventsub.SubscriptionPayload
        Итоговый список подписок для передачи в Conduit при старте.
    """
    subscriptions = build_owner_subscriptions(owner_id, bot_id)
    for user_id in public_user_ids:
        if user_id not in {owner_id, bot_id}:
            subscriptions.extend(build_public_subscriptions(user_id, bot_id))
    return subscriptions
