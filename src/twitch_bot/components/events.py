"""Реакции на события EventSub — фоллоу, рейды, подписки и всё остальное, что не команды чата."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from twitch_bot.core.base.component import PublicComponent

if TYPE_CHECKING:
    import twitchio

    from twitch_bot.core.bot import TwitchBot

logger = logging.getLogger(__name__)


class EventSubListeners(PublicComponent):
    """Слушает события чата и канала сразу на всех авторизованных каналах."""

    def is_owner_channel(self, broadcaster_id: str) -> bool:
        """Проверить, что событие пришло именно с канала владельца, а не со стороннего."""
        return broadcaster_id == self.bot.owner_id

    @PublicComponent.listener()
    async def event_message(self, payload: twitchio.ChatMessage) -> None:
        """Записать в лог каждое сообщение в чате — команды сюда не попадают, у них своя обработка."""
        logger.debug("[%s] %s: %s", payload.broadcaster.name, payload.chatter.name, payload.text)

    @PublicComponent.listener()
    async def event_stream_online(self, payload: twitchio.StreamOnline) -> None:
        """Отметить в логе, что канал начал стрим."""
        logger.info("Стрим онлайн: %s", payload.broadcaster.name)

    @PublicComponent.listener()
    async def event_stream_offline(self, payload: twitchio.StreamOffline) -> None:
        """Отметить в логе, что канал закончил стрим."""
        logger.info("Стрим оффлайн: %s", payload.broadcaster.name)

    @PublicComponent.listener(name="follow")
    async def event_follow(self, payload: twitchio.ChannelFollow) -> None:
        """Поблагодарить нового фолловера — но только если фоллоу случился на канале владельца."""
        if self.is_owner_channel(payload.broadcaster.id):
            await payload.broadcaster.send_message(
                sender=self.bot.bot_id,
                message=f"Спасибо за фоллоу, {payload.user.display_name}!",
            )

    @PublicComponent.listener(name="subscription")
    async def event_subscription(self, payload: twitchio.ChannelSubscribe) -> None:
        """Поблагодарить нового подписчика на канале владельца."""
        if self.is_owner_channel(payload.broadcaster.id):
            await payload.broadcaster.send_message(
                sender=self.bot.bot_id,
                message=f"Спасибо за подписку, {payload.user.display_name}!",
            )

    @PublicComponent.listener(name="raid")
    async def event_raid(self, payload: twitchio.ChannelRaid) -> None:
        """Записать в лог рейд, пришедший на канал владельца, вместе с числом зрителей."""
        if self.is_owner_channel(payload.to_broadcaster.id):
            logger.info("Рейд от %s, зрителей: %s", payload.from_broadcaster.display_name, payload.viewer_count)

    @PublicComponent.listener(name="custom_redemption_add")
    async def event_points_redeemed(self, payload: twitchio.ChannelPointsRedemptionAdd) -> None:
        """Записать в лог, кто и какую награду за channel points обменял на канале владельца."""
        if self.is_owner_channel(payload.broadcaster.id):
            logger.info("Channel points от %s: %s", payload.user.display_name, payload.reward.title)


async def setup(bot: TwitchBot) -> None:
    """Подключить к боту листенеры EventSub — точка входа, которую дёргает `load_module`.

    Parameters
    ----------
    bot : TwitchBot
        Бот, к которому добавляется компонент `EventSubListeners`.
    """
    await bot.add_component(EventSubListeners(bot))
