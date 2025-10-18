from __future__ import annotations
from typing import Any, Optional
from datetime import datetime, timedelta
from homeassistant.util import dt as dt_util
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

def _dig(data: dict, path: str, default=None):
    cur = data
    for p in path.split("."):
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur

SENSORS = [
    # Identità e stato di base
    ("name", "Nome Dispositivo", None, None, "mdi:label", None),
    ("version", "Firmware", None, None, "mdi:update", None),
    ("status", "Stato", None, None, "mdi:power", lambda v: "online" if v in (1, "1", True, "online") else "offline"),

    # Rete
    ("signal", "WiFi Segnale", None, "%", "mdi:wifi",
     lambda v: v if isinstance(v, (int, float)) else None),
    ("ssid", "SSID WiFi", None, None, "mdi:wifi", None),
    ("local_ip", "IP Locale", None, None, "mdi:ip", None),
    ("wan_ip", "IP WAN", None, None, "mdi:wan", None),

    # Sensori e stato operativo
    ("pir_status", "PIR Movimento", None, None, "mdi:motion-sensor",
     lambda v: "attivo" if v in (1, "1", True, "true") else "inattivo"),

    ("motion", "Movimento", None, None, "mdi:run",
     lambda v: "rilevato" if v in (1, "1", True, "true") else "nessuno"),

    # Ultimi eventi / diagnostica
    ("last_alarm_time", "Ultimo Allarme", None, None, "mdi:clock-alert", None),
    ("alarm_name", "Tipo Allarme", None, None, "mdi:alert", None),
    ("seconds_last_trigger", "Secondi Ultimo Movimento", None, "s", "mdi:timer", None),

    # Snapshot / foto ultima rilevazione
#    ("last_alarm_pic", "Ultima Istantanea", None, None, "mdi:camera", None),

    # Aggiornamenti firmware
    ("upgrade_available", "Aggiornamento Disponibile", None, None, "mdi:update",
     lambda v: "sì" if v in (1, "1", True, "true") else "no"),
]

async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    serial = data["serial"]
    ents = [Hp7Sensor(coordinator, serial, *cfg) for cfg in SENSORS]
    async_add_entities(ents)

class Hp7Sensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, serial, path, name, device_class, unit, icon, transform):
        super().__init__(coordinator)
        self._serial = serial
        self._path = path
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_{serial}_sensor_{path.replace('.', '_')}"
        self._attr_device_class = device_class
        self._unit = unit
        self._icon = icon
        self._transform = transform

    @property
    def native_unit_of_measurement(self) -> Optional[str]:
        return self._unit

    @property
    def icon(self) -> Optional[str]:
        return self._icon

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._serial)},
            name=f"EZVIZ HP7 ({self._serial})",
            manufacturer="EZVIZ",
            model="HP7",
        )

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        val = _dig(data, self._path)

        if self._attr_device_class == SensorDeviceClass.TIMESTAMP:
            if not val:
                return None
            try:
                from datetime import datetime
                from homeassistant.util import dt as dt_util
                dt = datetime.strptime(val, "%Y-%m-%d %H:%M:%S")
                return dt.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
            except Exception:
                return None

        if self._attr_device_class == SensorDeviceClass.DURATION:
            try:
                return float(val)
            except (TypeError, ValueError):
                return None

        if self._transform:
            try:
                val = self._transform(val)
            except Exception:
                pass
        return val