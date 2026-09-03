"""Media Player platform for JellyEmu active sessions."""
import logging
from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PLATFORM_COLORS
from .coordinator import JellyEmuCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the JellyEmu media player."""
    coordinator: JellyEmuCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([JellyEmuSessionMediaPlayer(coordinator, entry)], update_before_add=True)


class JellyEmuSessionMediaPlayer(CoordinatorEntity[JellyEmuCoordinator], MediaPlayerEntity):
    """Representation of an active JellyEmu emulation session as a media player."""

    def __init__(self, coordinator: JellyEmuCoordinator, entry: ConfigEntry) -> None:
        """Initialize the media player entity."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_name = "JellyEmu Now Playing"
        self._attr_unique_id = f"{entry.entry_id}_now_playing"
        self._attr_icon = "mdi:controller-classic"
        self._attr_supported_features = MediaPlayerEntityFeature(0)

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "JellyEmu Server",
            "manufacturer": "Jellyfin / JellyEmu",
            "model": "Emulation & Retro Gaming Hub",
            "sw_version": "1.0.0",
            "configuration_url": self.coordinator.url,
        }

    @property
    def current_session(self) -> dict | None:
        """Return the primary active session if one exists."""
        sessions = self.coordinator.data.get("active_sessions", [])
        return sessions[0] if sessions else None

    @property
    def state(self) -> MediaPlayerState:
        """State of the player."""
        if self.current_session:
            return MediaPlayerState.PLAYING
        return MediaPlayerState.IDLE

    @property
    def media_title(self) -> str | None:
        """Title of the currently playing game."""
        session = self.current_session
        return session.get("game_title") if session else None

    @property
    def media_artist(self) -> str | None:
        """User currently playing the game."""
        session = self.current_session
        return session.get("user_name") if session else None

    @property
    def media_series_title(self) -> str | None:
        """Platform / Console of the game."""
        session = self.current_session
        return session.get("platform") if session else None

    @property
    def media_album_name(self) -> str | None:
        """Console platform name."""
        return self.media_series_title

    @property
    def entity_picture(self) -> str | None:
        """Box art / cover image for the game."""
        session = self.current_session
        return session.get("image_url") if session else None

    @property
    def media_position(self) -> int | None:
        """Elapsed session time in seconds."""
        session = self.current_session
        return session.get("seconds_elapsed") if session else None

    @property
    def media_content_type(self) -> MediaType:
        """Content type."""
        return MediaType.GAME

    @property
    def app_name(self) -> str:
        """App name."""
        return "JellyEmu"

    @property
    def extra_state_attributes(self) -> dict:
        """Attributes for automations (lighting, notifications)."""
        session = self.current_session
        platform = (session.get("platform") or "").lower() if session else ""
        color = PLATFORM_COLORS.get(platform, "#00E5FF")

        return {
            "server_url": self.coordinator.url,
            "active_players_count": self.coordinator.data.get("active_count", 0),
            "platform_theme_color": color,
            "play_url": session.get("play_url") if session else None,
            "device_name": session.get("device_name") if session else None,
            "all_sessions": self.coordinator.data.get("active_sessions", []),
        }
