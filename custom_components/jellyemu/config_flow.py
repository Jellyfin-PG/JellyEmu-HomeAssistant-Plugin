"""Config flow for JellyEmu integration."""
import logging
import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import aiohttp_client
from homeassistant.core import callback

from .const import CONF_API_KEY, CONF_URL, CONF_VERIFY_SSL, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL, default="http://localhost:8096"): str,
        vol.Required(CONF_API_KEY): str,
        vol.Optional(CONF_VERIFY_SSL, default=True): bool,
    }
)


async def validate_input(hass, data: dict):
    """Validate the user input allows us to connect to Jellyfin."""
    url = data[CONF_URL].rstrip("/")
    api_key = data[CONF_API_KEY]
    verify_ssl = data.get(CONF_VERIFY_SSL, True)

    session = aiohttp_client.async_get_clientsession(hass, verify_ssl=verify_ssl)

    headers = {
        "X-Emby-Token": api_key,
        "Accept": "application/json",
    }

    try:
        async with session.get(f"{url}/System/Info", headers=headers, timeout=10) as resp:
            if resp.status in (401, 403):
                return {"error": "invalid_auth"}
            if resp.status != 200:
                return {"error": "cannot_connect"}
            info = await resp.json()
            server_name = info.get("ServerName", "Jellyfin")
            server_id = info.get("Id", "jellyfin-default")
            return {"title": f"JellyEmu ({server_name})", "server_id": server_id, "url": url}
    except aiohttp.ClientConnectorError:
        return {"error": "cannot_connect"}
    except Exception as ex:
        _LOGGER.exception("Unexpected exception connecting to Jellyfin: %s", ex)
        return {"error": "unknown"}


class JellyEmuConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for JellyEmu."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            user_input[CONF_URL] = user_input[CONF_URL].rstrip("/")
            res = await validate_input(self.hass, user_input)

            if "error" in res:
                errors["base"] = res["error"]
            else:
                await self.async_set_unique_id(res.get("server_id"))
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=res.get("title", "JellyEmu"),
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
