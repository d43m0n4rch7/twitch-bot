"""EventSub listeners kept separate from command modules."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from twitch_bot.core.base.component import PublicComponent

if TYPE_CHECKING:
    import twitchio

    from twitch_bot.core.bot import TwitchBot

logger = logging.getLogger(__name__)


class EventSubListeners(PublicComponent):
    """Listeners for chat messages and channel events across authorized channels."""

    def is_owner_channel(self, broadcaster_id: str) -> bool:
        """Return whether an event belongs to the configured owner channel.

        Parameters
        ----------
        broadcaster_id : str
            Twitch user ID of the event broadcaster.

        Returns
        -------
        bool
            ``True`` when the broadcaster is the bot owner channel.
        """
        return broadcaster_id == self.bot.owner_id

    @PublicComponent.listener()
    async def event_message(self, payload: twitchio.ChatMessage) -> None:
        """Log incoming chat messages at debug level.

        Parameters
        ----------
        payload : twitchio.ChatMessage
            Chat message event from EventSub.
        """
        logger.debug("[%s] %s: %s", payload.broadcaster.name, payload.chatter.name, payload.text)

    @PublicComponent.listener()
    async def event_stream_online(self, payload: twitchio.StreamOnline) -> None:
        """Log when a subscribed channel goes live.

        Parameters
        ----------
        payload : twitchio.StreamOnline
            Stream online event from EventSub.
        """
        logger.info("Stream online: %s", payload.broadcaster.name)

    @PublicComponent.listener()
    async def event_stream_offline(self, payload: twitchio.StreamOffline) -> None:
        """Log when a subscribed channel goes offline.

        Parameters
        ----------
        payload : twitchio.StreamOffline
            Stream offline event from EventSub.
        """
        logger.info("Stream offline: %s", payload.broadcaster.name)

    @PublicComponent.listener(name="follow")
    async def event_follow(self, payload: twitchio.ChannelFollow) -> None:
        """Thank a new follower in the owner's channel.

        Parameters
        ----------
        payload : twitchio.ChannelFollow
            Follow event from EventSub.
        """
        if self.is_owner_channel(payload.broadcaster.id):
            await payload.broadcaster.send_message(
                sender=self.bot.bot_id,
                message=f"Thanks for the follow, {payload.user.display_name}!",
            )

    @PublicComponent.listener(name="subscription")
    async def event_subscription(self, payload: twitchio.ChannelSubscribe) -> None:
        """Thank a new subscriber in the owner's channel.

        Parameters
        ----------
        payload : twitchio.ChannelSubscribe
            Subscription event from EventSub.
        """
        if self.is_owner_channel(payload.broadcaster.id):
            await payload.broadcaster.send_message(
                sender=self.bot.bot_id,
                message=f"Thanks for subscribing, {payload.user.display_name}!",
            )

    @PublicComponent.listener(name="raid")
    async def event_raid(self, payload: twitchio.ChannelRaid) -> None:
        """Log an incoming raid on the owner's channel.

        Parameters
        ----------
        payload : twitchio.ChannelRaid
            Raid event from EventSub.
        """
        if self.is_owner_channel(payload.to_broadcaster.id):
            logger.info(
                "Raid from %s with %s viewers",
                payload.from_broadcaster.display_name,
                payload.viewer_count,
            )

    @PublicComponent.listener(name="custom_redemption_add")
    async def event_points_redeemed(self, payload: twitchio.ChannelPointsRedemptionAdd) -> None:
        """Log a channel-points redemption on the owner's channel.

        Parameters
        ----------
        payload : twitchio.ChannelPointsRedemptionAdd
            Redemption event from EventSub.
        """
        if self.is_owner_channel(payload.broadcaster.id):
            logger.info(
                "Channel points redeemed by %s: %s",
                payload.user.display_name,
                payload.reward.title,
            )


async def setup(bot: TwitchBot) -> None:
    """Register EventSub listener components.

    Parameters
    ----------
    bot : TwitchBot
        Application bot that receives the component.
    """
    await bot.add_component(EventSubListeners(bot))
