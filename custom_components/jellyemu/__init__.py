"""The JellyEmu Home Assistant Integration."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.components import persistent_notification

from .const import DOMAIN, PLATFORMS, SERVICE_LAUNCH_GAME, ATTR_ITEM_ID, ATTR_USER_ID, ATTR_GAME_TITLE
from .coordinator import JellyEmuCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the JellyEmu component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up JellyEmu from a config entry."""
    coordinator = JellyEmuCoordinator(hass, entry.data)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def handle_launch_game(call: ServiceCall):
        """Service to generate a direct play link or notification."""
        item_id = call.data.get(ATTR_ITEM_ID)
        user_id = call.data.get(ATTR_USER_ID, "")
        title = call.data.get(ATTR_GAME_TITLE, "Retro Game")

        play_url = f"{coordinator.url}/jellyemu/play/{item_id}"
        if user_id:
            play_url += f"?userId={user_id}"

        _LOGGER.info("JellyEmu Launch Game triggered for '%s' (ID: %s)", title, item_id)

        # Fire Home Assistant event so automations (like casting or browser mod) can catch it
        hass.bus.async_fire(
            "jellyemu_launch_game",
            {
                "item_id": item_id,
                "user_id": user_id,
                "title": title,
                "url": play_url,
            },
        )

        persistent_notification.async_create(
            hass,
            f"Click here to play **[{title}]({play_url})** on your device.",
            title="🎮 JellyEmu Ready to Play",
            notification_id=f"jellyemu_launch_{item_id}",
        )

    hass.services.async_register(DOMAIN, SERVICE_LAUNCH_GAME, handle_launch_game)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok
