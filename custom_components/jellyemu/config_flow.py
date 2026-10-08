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
        "Authorization": f'MediaBrowser Token="{api_key}"',
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

    def _get_reconfigure_entry_compat(self) -> config_entries.ConfigEntry:
        """Get the config entry to reconfigure across different HA versions."""
        if hasattr(self, "_get_reconfigure_entry"):
            return self._get_reconfigure_entry()
        return self.hass.config_entries.async_get_entry(self.context["entry_id"])

    async def async_step_reconfigure(self, user_input=None):
        """Handle a reconfiguration flow initialized by the user."""
        errors = {}
        entry = self._get_reconfigure_entry_compat()

        if user_input is not None:
            user_input[CONF_URL] = user_input[CONF_URL].rstrip("/")
            res = await validate_input(self.hass, user_input)

            if "error" in res:
                errors["base"] = res["error"]
            else:
                await self.async_set_unique_id(res.get("server_id"))
                if hasattr(self, "_abort_if_unique_id_mismatch"):
                    self._abort_if_unique_id_mismatch(reason="wrong_server")

                if hasattr(self, "async_update_reload_and_abort"):
                    return self.async_update_reload_and_abort(
                        entry,
                        data={**entry.data, **user_input},
                        title=res.get("title", entry.title),
                        reason="reconfigure_successful",
                    )

                self.hass.config_entries.async_update_entry(
                    entry,
                    data={**entry.data, **user_input},
                    title=res.get("title", entry.title),
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reconfigure_successful")

        current_url = entry.data.get(CONF_URL, "http://localhost:8096")
        current_api_key = entry.data.get(CONF_API_KEY, "")
        current_verify_ssl = entry.data.get(CONF_VERIFY_SSL, True)

        schema = vol.Schema(
            {
                vol.Required(CONF_URL, default=current_url): str,
                vol.Required(CONF_API_KEY, default=current_api_key): str,
                vol.Optional(CONF_VERIFY_SSL, default=current_verify_ssl): bool,
            }
        )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return JellyEmuOptionsFlow(config_entry)


class JellyEmuOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for JellyEmu."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage connection options."""
        errors = {}

        if user_input is not None:
            user_input[CONF_URL] = user_input[CONF_URL].rstrip("/")
            res = await validate_input(self.hass, user_input)

            if "error" in res:
                errors["base"] = res["error"]
            else:
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={**self.config_entry.data, **user_input},
                    title=res.get("title", self.config_entry.title),
                )
                await self.hass.config_entries.async_reload(self.config_entry.entry_id)
                return self.async_create_entry(title="", data={})

        current_url = self.config_entry.data.get(CONF_URL, "http://localhost:8096")
        current_api_key = self.config_entry.data.get(CONF_API_KEY, "")
        current_verify_ssl = self.config_entry.data.get(CONF_VERIFY_SSL, True)

        schema = vol.Schema(
            {
                vol.Required(CONF_URL, default=current_url): str,
                vol.Required(CONF_API_KEY, default=current_api_key): str,
                vol.Optional(CONF_VERIFY_SSL, default=current_verify_ssl): bool,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
        )
