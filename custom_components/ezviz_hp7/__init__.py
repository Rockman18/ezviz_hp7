from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN, PLATFORMS
from .api import Hp7Api
from .coordinator import Hp7Coordinator

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    username = entry.data["username"]
    password = entry.data["password"]
    region = entry.data["region"]
    serial = entry.data["serial"]

    token = entry.data.get("token")

    api = Hp7Api(username, password, region, token=token)
    await hass.async_add_executor_job(api.login)

    await hass.async_add_executor_job(api.detect_capabilities, serial)

    coordinator = Hp7Coordinator(hass, api, serial)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "api": api,
        "serial": serial,
        "coordinator": coordinator,
        "token": api._token,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True
