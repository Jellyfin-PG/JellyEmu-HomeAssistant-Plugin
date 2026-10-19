"""The JellyEmu Home Assistant Integration."""
import json
import logging
from pathlib import Path

from homeassistant.components import persistent_notification
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN, PLATFORMS, SERVICE_LAUNCH_GAME, ATTR_ITEM_ID, ATTR_USER_ID, ATTR_GAME_TITLE
from .coordinator import JellyEmuCoordinator

_LOGGER = logging.getLogger(__name__)


def _get_card_version() -> str:
    """Read version from manifest.json."""
    manifest_path = Path(__file__).parent / "manifest.json"
    if manifest_path.is_file():
        try:
            with open(manifest_path, encoding="utf-8") as f:
                return json.load(f).get("version", "1.0.0")
        except Exception:
            pass
    return "1.0.0"


async def async_register_card(hass: HomeAssistant) -> None:
    """Register JellyEmu card static path and dashboard resource."""
    www_dir = Path(__file__).parent / "www"
    if not www_dir.is_dir():
        return

    # Register static path to serve custom_components/jellyemu/www under /jellyemu
    if not hass.data.get(DOMAIN, {}).get("static_path_registered"):
        try:
            if hasattr(hass.http, "async_register_static_paths"):
                await hass.http.async_register_static_paths([
                    StaticPathConfig("/jellyemu", str(www_dir), cache_headers=False)
                ])
            elif hasattr(hass.http, "register_static_path"):
                hass.http.register_static_path("/jellyemu", str(www_dir), cache_headers=False)
            hass.data.setdefault(DOMAIN, {})["static_path_registered"] = True
            _LOGGER.debug("Registered JellyEmu static path for %s", www_dir)
        except Exception as err:
            _LOGGER.debug("Could not register JellyEmu static path: %s", err)

    # Automatically register card as a Lovelace dashboard resource
    async def _async_register_resource(_event=None) -> None:
        try:
            lovelace = hass.data.get("lovelace")
            if not lovelace:
                return

            resources = getattr(lovelace, "resources", None)
            if not resources or not hasattr(resources, "async_create_item"):
                return

            if hasattr(resources, "loaded") and not resources.loaded:
                await resources.async_load()

            card_version = _get_card_version()
            card_url = f"/jellyemu/jellyemu-card.js?v={card_version}"

            items = resources.async_items() if hasattr(resources, "async_items") else []
            for item in items:
                url = item.get("url", "")
                if "/jellyemu/jellyemu-card.js" in url:
                    if url != card_url and hasattr(resources, "async_update_item"):
                        await resources.async_update_item(
                            item["id"], {"res_type": "module", "url": card_url}
                        )
                        _LOGGER.debug("Updated JellyEmu card resource to %s", card_url)
                    return

            await resources.async_create_item(
                {"res_type": "module", "url": card_url}
            )
            _LOGGER.info("Automatically registered JellyEmu card dashboard resource: %s", card_url)
        except Exception as err:
            _LOGGER.debug("Could not register JellyEmu card resource: %s", err)

    if hass.is_running:
        await _async_register_resource()
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _async_register_resource)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the JellyEmu component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up JellyEmu from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    await async_register_card(hass)

    coordinator = JellyEmuCoordinator(hass, entry.data)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

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
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_LAUNCH_GAME)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)

