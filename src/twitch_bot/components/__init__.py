"""Компоненты, которые идут с ботом «из коробки»."""

__all__ = ["COMPONENT_MODULES"]

# Пути модулей, которые TwitchBot.setup_hook загружает по очереди при старте.
# Хотите добавить свой компонент — просто впишите его сюда.
COMPONENT_MODULES: tuple[str, ...] = (
    "twitch_bot.components.basic",
    "twitch_bot.components.events",
)
