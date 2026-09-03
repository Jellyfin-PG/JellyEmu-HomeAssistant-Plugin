"""DataUpdateCoordinator for JellyEmu."""
from datetime import timedelta
import logging
import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers import aiohttp_client

from .const import (
    CONF_API_KEY,
    CONF_URL,
    CONF_VERIFY_SSL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    resolve_system_platform,
)

_LOGGER = logging.getLogger(__name__)


class JellyEmuCoordinator(DataUpdateCoordinator):
    """Class to manage fetching JellyEmu data from Jellyfin server."""

    def __init__(self, hass: HomeAssistant, entry_data: dict) -> None:
        """Initialize the coordinator."""
        self.url = entry_data[CONF_URL].rstrip("/")
        self.api_key = entry_data[CONF_API_KEY]
        verify_ssl = entry_data.get(CONF_VERIFY_SSL, True)
        self.session = aiohttp_client.async_get_clientsession(hass, verify_ssl=verify_ssl)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    @property
    def headers(self) -> dict:
        """Standard Jellyfin authorization headers."""
        return {
            "X-Emby-Token": self.api_key,
            "Accept": "application/json",
        }

    async def _async_update_data(self) -> dict:
        """Fetch data from Jellyfin and JellyEmu endpoints."""
        data = {
            "active_sessions": [],
            "active_count": 0,
            "total_games": 0,
            "systems_count": 0,
            "systems": [],
            "leaderboard": [],
            "total_playtime_seconds": 0,
            "games": [],
            "server_url": self.url,
        }

        try:
            # Fetch Active Sessions from Jellyfin
            async with self.session.get(f"{self.url}/Sessions", headers=self.headers, timeout=10) as resp:
                if resp.status == 200:
                    sessions = await resp.json()
                    data["active_sessions"] = self._parse_active_sessions(sessions)
                    data["active_count"] = len(data["active_sessions"])

            # Fetch Total Playtime across all users
            try:
                #  Direct aggregate endpoint
                async with self.session.get(
                    f"{self.url}/jellyemu/playtime/total", headers=self.headers, timeout=8
                ) as resp:
                    if resp.status == 200:
                        res = await resp.json()
                        data["total_playtime_seconds"] = res.get("totalSeconds", 0)
                    else:
                        raise ValueError("Fallback to per-user query")
            except Exception:
                # Fallback: Query all users and sum their playtimes
                try:
                    async with self.session.get(
                        f"{self.url}/Users", headers=self.headers, timeout=8
                    ) as u_resp:
                        if u_resp.status == 200:
                            users = await u_resp.json()
                            grand_total = 0
                            for u in users:
                                uid = u.get("Id")
                                if not uid:
                                    continue
                                try:
                                    async with self.session.get(
                                        f"{self.url}/jellyemu/playtime/{uid}", headers=self.headers, timeout=5
                                    ) as pt_resp:
                                        if pt_resp.status == 200:
                                            pt = await pt_resp.json()
                                            grand_total += pt.get("totalSeconds", 0)
                                except Exception:
                                    pass
                            data["total_playtime_seconds"] = grand_total
                except Exception as ex:
                    _LOGGER.debug("Could not aggregate user playtimes: %s", ex)

            # Fetch Retro Games Catalog & Systems via standard Jellyfin API
            try:
                params = {
                    "IncludeItemTypes": "Book",
                    "Tags": "JellyEmu",
                    "Recursive": "true",
                    "Fields": "Tags,PremiereDate",
                    "SortBy": "SortName",
                }

                async with self.session.get(
                    f"{self.url}/Items", headers=self.headers, params=params, timeout=10
                ) as resp:
                    items = []
                    total_count = 0
                    if resp.status == 200:
                        items_data = await resp.json()
                        items = items_data.get("Items", [])
                        total_count = items_data.get("TotalRecordCount", len(items))

                data["total_games"] = total_count
                systems_found = set()
                game_list = []

                for item in items:
                    item_id = item.get("Id")
                    name = item.get("Name", "Unknown Game")
                    raw_tags = item.get("Tags", [])
                    platform = resolve_system_platform(raw_tags)
                    systems_found.add(platform)

                    image_url = f"{self.url}/Items/{item_id}/Images/Primary?fillWidth=300&quality=85&api_key={self.api_key}"
                    play_url = f"{self.url}/jellyemu/play/{item_id}"
                    details_url = f"{self.url}/web/index.html#!/details?id={item_id}"

                    game_list.append(
                        {
                            "id": item_id,
                            "name": name,
                            "platform": platform,
                            "image": image_url,
                            "play_url": play_url,
                            "details_url": details_url,
                            "year": item.get("PremiereDate", "")[:4] if item.get("PremiereDate") else "",
                        }
                    )

                data["games"] = game_list
                data["systems"] = sorted(list(systems_found))
                data["systems_count"] = len(data["systems"])
            except Exception as ex:
                _LOGGER.debug("Could not fetch game library catalog: %s", ex)

            return data

        except Exception as err:
            raise UpdateFailed(f"Error communicating with Jellyfin/JellyEmu: {err}") from err

    def _parse_active_sessions(self, sessions: list) -> list:
        """Filter and structure active emulation sessions."""
        active = []
        for s in sessions:
            client = s.get("Client", "")
            now_playing = s.get("NowPlayingItem")

            # Check if this session is an active JellyEmu game session
            is_jellyemu = (
                client == "JellyEmu"
                or (now_playing and now_playing.get("Type") in ("Game", "Book"))
                or "jellyemu" in s.get("DeviceId", "").lower()
            )

            if is_jellyemu and now_playing:
                item_id = now_playing.get("Id")
                game_title = now_playing.get("Name", "Unknown Game")
                user_name = s.get("UserName", "Unknown User")
                user_id = s.get("UserId", "")
                device_name = s.get("DeviceName", s.get("Client", "JellyEmu"))
                ticks = s.get("PlayState", {}).get("PositionTicks", 0)
                seconds_elapsed = round(ticks / 10000000) if ticks else 0

                tags = now_playing.get("Tags", [])
                platform = resolve_system_platform(tags)

                image_url = (
                    f"{self.url}/Items/{item_id}/Images/Primary?fillWidth=400&quality=90"
                    if item_id
                    else ""
                )

                active.append(
                    {
                        "session_id": s.get("Id"),
                        "user_name": user_name,
                        "user_id": user_id,
                        "device_name": device_name,
                        "item_id": item_id,
                        "game_title": game_title,
                        "platform": platform,
                        "seconds_elapsed": seconds_elapsed,
                        "image_url": image_url,
                        "play_url": f"{self.url}/jellyemu/play/{item_id}",
                    }
                )
        return active
