"""Builders for the EventSub subscription payloads used by the bot."""

from __future__ import annotations

from typing import TYPE_CHECKING

from twitchio import eventsub

if TYPE_CHECKING:
    from collections.abc import Iterable

__all__ = [
    "build_owner_subscriptions",
    "build_public_subscriptions",
    "build_subscriptions",
]


def build_public_subscriptions(
    broadcaster_id: str,
    bot_id: str,
) -> list[eventsub.SubscriptionPayload]:
    """Build the basic EventSub set for a public broadcaster.

    Parameters
    ----------
    broadcaster_id : str
        Twitch user ID of the broadcaster.
    bot_id : str
        Twitch user ID of the bot account receiving chat events.

    Returns
    -------
    list of eventsub.SubscriptionPayload
        Chat message and stream online/offline subscriptions.
    """
    return [
        eventsub.ChatMessageSubscription(broadcaster_user_id=broadcaster_id, user_id=bot_id),
        eventsub.StreamOnlineSubscription(broadcaster_user_id=broadcaster_id),
        eventsub.StreamOfflineSubscription(broadcaster_user_id=broadcaster_id),
    ]


def build_owner_subscriptions(
    owner_id: str,
    bot_id: str,
) -> list[eventsub.SubscriptionPayload]:
    """Build the extended EventSub set for the bot owner's channel.

    Parameters
    ----------
    owner_id : str
        Twitch user ID of the owner channel.
    bot_id : str
        Twitch user ID of the bot account.

    Returns
    -------
    list of eventsub.SubscriptionPayload
        Public subscriptions plus follow, raid, subscribe, points, update and ban.
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
    owner_id: str,
    bot_id: str,
    public_user_ids: Iterable[str],
) -> list[eventsub.SubscriptionPayload]:
    """Build the combined owner and public EventSub subscriptions for startup.

    Parameters
    ----------
    owner_id : str
        Twitch user ID of the owner channel.
    bot_id : str
        Twitch user ID of the bot account.
    public_user_ids : iterable of str
        Twitch user IDs of other channels with persisted OAuth credentials.

    Returns
    -------
    list of eventsub.SubscriptionPayload
        Deduplicated owner and public subscriptions.
    """
    subscriptions = build_owner_subscriptions(owner_id, bot_id)
    known = {owner_id, bot_id}
    for user_id in public_user_ids:
        if user_id not in known:
            subscriptions.extend(build_public_subscriptions(user_id, bot_id))
            known.add(user_id)
    return subscriptions
