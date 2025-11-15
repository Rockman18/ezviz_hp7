from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN


def _to_bool(v) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("1", "true", "on", "yes", "y"):
            return True
        return False
    return False


ALARM_FIELD = "alarm_name"
ALARM_TIME_FIELD = "last_alarm_time"

PULSE_SECONDS = 3

SIMPLE_MAP = [
    ("Motion_Trigger", "motion_trigger", BinarySensorDeviceClass.MOTION),
]

ALARM_MAP = [
    (["Smart Detection Alarm"], "Citofono - Allarme Smart Detection", "smart_detection_alarm", None, "mdi:run"),
    (["Intelligent Detection Alarm"], "Citofono - Allarme Intelligente", "intelligent_detection_alarm", None, "mdi:account-search"),
    (["Your doorbell is ringing"], "Citofono – Campanello", "doorbell_ringing", None, "mdi:doorbell"),
    (["EZVIZ app open the gate", "open the gate"], "Citofono – Cancello", "gate_open", None, "mdi:gate-open"),
    (["EZVIZ app unlock the lock"], "Citofono – Serratura", "unlock_lock", None, "mdi:lock-open-variant"),
]


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    serial = data["serial"]

    ents: list[BinarySensorEntity] = []

    for key, translation_key, dc in SIMPLE_MAP:
        ents.append(Hp7BinarySimple(coordinator, serial, key, translation_key, dc))

    for match_values, name, unique_suffix, dc, icon in ALARM_MAP:
        ents.append(
            Hp7BinaryAlarm(
                coordinator,
                serial,
                match_values,
                name,
                unique_suffix,
                dc,
                icon,
            )
        )

    async_add_entities(ents)


class Hp7BinarySimple(CoordinatorEntity, BinarySensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, serial: str, key: str, translation_key: str, device_class):
        super().__init__(coordinator)
        self._serial = serial
        self._key = key
        self._attr_translation_key = translation_key
        self._attr_unique_id = f"{DOMAIN}_{serial}_binary_{key}"
        self._attr_device_class = device_class

    @property
    def is_on(self) -> bool:
        data = self.coordinator.data or {}
        val = data.get(self._key)
        return _to_bool(val)

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._serial)},
            name=f"EZVIZ HP7 ({self._serial})",
            manufacturer="EZVIZ",
            model="HP7",
        )


class Hp7BinaryAlarm(CoordinatorEntity, BinarySensorEntity):
    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator,
        serial: str,
        match_values: list[str],
        name: str,
        unique_suffix: str,
        device_class,
        icon: str,
    ):
        super().__init__(coordinator)
        self._serial = serial
        self._match_values = match_values

        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_{serial}_alarm_{unique_suffix}"
        self._attr_device_class = device_class
        self._attr_icon = icon

        self._last_trigger = None
        self._prev_alarm_time = None
        self._off_unsub = None

    @property
    def is_on(self) -> bool:
        """ON solo per PULSE_SECONDS dopo l'ultimo trigger."""
        if self._last_trigger is None:
            return False
        delta = (dt_util.utcnow() - self._last_trigger).total_seconds()
        return delta < PULSE_SECONDS

    def _schedule_state_update(self):
        """Programma un aggiornamento stato dopo PULSE_SECONDS per far tornare OFF."""
        if self._off_unsub:
            self._off_unsub()

        def _cb(_now):
            self.async_write_ha_state()

        self._off_unsub = async_call_later(self.hass, PULSE_SECONDS, _cb)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Chiamato quando arrivano nuovi dati dal coordinator."""
        data = self.coordinator.data or {}
        current_alarm = data.get(ALARM_FIELD)
        current_alarm_time = data.get(ALARM_TIME_FIELD)

        if (
            current_alarm in self._match_values
            and current_alarm_time is not None
            and current_alarm_time != self._prev_alarm_time
        ):
            self._prev_alarm_time = current_alarm_time
            self._last_trigger = dt_util.utcnow()
            self._schedule_state_update()

        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._serial)},
            name=f"EZVIZ HP7 ({self._serial})",
            manufacturer="EZVIZ",
            model="HP7",
        )
