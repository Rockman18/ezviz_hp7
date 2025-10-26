from __future__ import annotations
import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN, CONF_REGION, CONF_SERIAL
from .api import Hp7Api
import logging

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema({
    vol.Required("username"): str,
    vol.Required("password"): str,
    vol.Required(CONF_REGION, default="eu"): vol.In(["eu", "us", "cn", "as", "sa", "ru"]),
})

SERIAL_SCHEMA = vol.Schema({
    vol.Required(CONF_SERIAL): str,
})

def _looks_like_long_serial(s: str) -> bool:
    # euristica semplice: molti HP7 espongono long serial con '-' oppure stringhe più lunghe
    return ("-" in s) or (len(s) >= 12)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._cached_creds: dict | None = None
        self._device_options: dict[str, str] | None = None
        self._serial_to_unique: dict[str, str] | None = None

    async def async_step_user(self, user_input=None):
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA)

        api = Hp7Api(user_input["username"], user_input["password"], user_input[CONF_REGION])
        try:
            ok = await self.hass.async_add_executor_job(api.login)
            if not ok:
                raise RuntimeError("login_failed")

            if getattr(api, "_token", None):
                user_input["token"] = api._token

            devices: dict[str, dict] = {}
            if hasattr(api, "list_devices"):
                devices = await self.hass.async_add_executor_job(api.list_devices)
        except Exception as e:
            _LOGGER.exception("EZVIZ login/list_devices failed: %s", e)
            return self.async_show_form(
                step_id="user",
                data_schema=DATA_SCHEMA,
                errors={"base": "auth"},
            )

        # Costruisci opzioni filtrando i serial corti/duplicati
        options: dict[str, str] = {}
        serial_to_unique: dict[str, str] = {}

        for serial_key, info in (devices or {}).items():
            name = (info.get("name") or info.get("device_name") or "Device").strip()

            # Prova a pescare un ID davvero unico/stabile fornito dall'API, se esiste
            api_unique = (
                info.get("device_id")
                or info.get("uuid")
                or info.get("serial_long")
                or info.get("full_serial")
                or None
            )

            # Scegli quale serial mostrare all’utente:
            # 1) preferisci serial “lunghi” (euristica)
            # 2) se il key è corto ma info contiene un long, usa quello
            if _looks_like_long_serial(serial_key):
                shown_serial = serial_key
            else:
                shown_serial = (
                    info.get("serial_long")
                    or info.get("full_serial")
                    or None
                )

            # Se ancora niente di “lungo”, scarta questa entry (evita doppione corto)
            if not shown_serial:
                # come fallback estrema, se non hai long, puoi decidere di mostrare
                # anche il corto; qui scegliamo di saltarlo per evitare doppioni
                continue

            # Unique ID per HA: meglio un id stabile dell’API; altrimenti il long serial
            unique_id = api_unique or shown_serial

            # Evita duplicati se più record puntano allo stesso device
            if shown_serial in options or unique_id in serial_to_unique.values():
                continue

            options[shown_serial] = f"{name} ({shown_serial})"
            serial_to_unique[shown_serial] = unique_id

        self._cached_creds = user_input

        if options:
            self._device_options = options
            self._serial_to_unique = serial_to_unique
            return await self.async_step_pick_serial()

        # Nessun device elencato: chiedi serial manualmente
        return await self.async_step_enter_serial()

    async def async_step_pick_serial(self, user_input=None):
        assert self._device_options is not None, "Device list not prepared"

        schema = vol.Schema({
            vol.Required(CONF_SERIAL): vol.In(list(self._device_options.keys()))
        })

        if user_input is None:
            return self.async_show_form(step_id="pick_serial", data_schema=schema)

        serial = user_input[CONF_SERIAL]

        # Usa unique_id stabile se l’abbiamo
        unique_id = None
        if self._serial_to_unique:
            unique_id = self._serial_to_unique.get(serial)

        await self.async_set_unique_id(unique_id or serial)
        self._abort_if_unique_id_configured()

        data = {**(self._cached_creds or {}), CONF_SERIAL: serial}
        title = f"EZVIZ HP7 ({serial})"
        return self.async_create_entry(title=title, data=data)

    async def async_step_enter_serial(self, user_input=None):
        if user_input is None:
            return self.async_show_form(step_id="enter_serial", data_schema=SERIAL_SCHEMA)

        serial = user_input[CONF_SERIAL]

        # Se l’utente inserisce a mano, prova a normalizzare:
        norm_serial = serial.strip()
        await self.async_set_unique_id(norm_serial)
        self._abort_if_unique_id_configured()

        data = {**(self._cached_creds or {}), CONF_SERIAL: norm_serial}
        title = f"EZVIZ HP7 ({norm_serial})"
        return self.async_create_entry(title=title, data=data)
