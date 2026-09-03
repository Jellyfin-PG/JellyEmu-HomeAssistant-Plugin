"""Sensor platform for JellyEmu."""
import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import JellyEmuCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the JellyEmu sensors."""
    coordinator: JellyEmuCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        JellyEmuActivePlayersSensor(coordinator, entry),
        JellyEmuTotalGamesSensor(coordinator, entry),
        JellyEmuSystemsSensor(coordinator, entry),
        JellyEmuTotalPlaytimeSensor(coordinator, entry),
    ]

    async_add_entities(entities, update_before_add=True)


class JellyEmuBaseSensor(CoordinatorEntity[JellyEmuCoordinator], SensorEntity):
    """Base sensor for JellyEmu."""

    def __init__(self, coordinator: JellyEmuCoordinator, entry: ConfigEntry, sub_key: str, name: str) -> None:
        """Initialize base entity."""
        super().__init__(coordinator)
        self._entry = entry
        self._sub_key = sub_key
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{sub_key}"

    @property
    def device_info(self):
        """Return device information about the Jellyfin/JellyEmu server."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "JellyEmu Server",
            "manufacturer": "Jellyfin / JellyEmu",
            "model": "Emulation & Retro Gaming Hub",
            "sw_version": "1.0.0",
            "configuration_url": self.coordinator.url,
        }


class JellyEmuActivePlayersSensor(JellyEmuBaseSensor):
    """Sensor reporting the number of users actively playing games right now."""

    def __init__(self, coordinator: JellyEmuCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "active_players", "JellyEmu Active Players")
        self._attr_icon = "mdi:gamepad-variant"

    @property
    def native_value(self) -> int:
        return self.coordinator.data.get("active_count", 0)

    @property
    def extra_state_attributes(self) -> dict:
        sessions = self.coordinator.data.get("active_sessions", [])
        return {
            "active_sessions": sessions,
            "players": [s.get("user_name") for s in sessions],
            "games": [s.get("game_title") for s in sessions],
            "consoles": [s.get("platform") for s in sessions],
        }


class JellyEmuTotalGamesSensor(JellyEmuBaseSensor):
    """Sensor reporting total ROMs/games in the library."""

    def __init__(self, coordinator: JellyEmuCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "total_games", "JellyEmu Total Games")
        self._attr_icon = "mdi:folder-multiple-image"

    @property
    def native_value(self) -> int:
        return self.coordinator.data.get("total_games", 0)

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "server_url": self.coordinator.url,
            "total_games": self.coordinator.data.get("total_games", 0),
            "systems": self.coordinator.data.get("systems", []),
            "games": self.coordinator.data.get("games", []),
        }


class JellyEmuSystemsSensor(JellyEmuBaseSensor):
    """Sensor reporting count of supported retro consoles."""

    def __init__(self, coordinator: JellyEmuCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "systems_count", "JellyEmu Supported Systems")
        self._attr_icon = "mdi:controller"

    @property
    def native_value(self) -> int:
        return self.coordinator.data.get("systems_count", 0)

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "systems": self.coordinator.data.get("systems", []),
        }


class JellyEmuTotalPlaytimeSensor(JellyEmuBaseSensor):
    """Sensor reporting total hours played in the household."""

    def __init__(self, coordinator: JellyEmuCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "total_playtime", "JellyEmu Total Playtime")
        self._attr_icon = "mdi:timer-outline"
        self._attr_native_unit_of_measurement = "h"

    @property
    def native_value(self) -> float:
        total_secs = self.coordinator.data.get("total_playtime_seconds", 0)
        return round(total_secs / 3600.0, 1)
