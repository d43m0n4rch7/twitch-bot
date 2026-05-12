"""Built-in bot components loaded at startup.

Each module listed in :data:`COMPONENT_MODULES` exports an async ``setup(bot)``
function (TwitchIO module protocol) and can be hot-reloaded independently.
"""

__all__ = ["COMPONENT_MODULES"]

COMPONENT_MODULES: tuple[str, ...] = (
    "twitch_bot.components.basic",
    "twitch_bot.components.events",
)
