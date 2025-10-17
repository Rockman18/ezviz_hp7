from __future__ import annotations
import logging
from datetime import timedelta, datetime
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .const import UPDATE_INTERVAL_SEC
from .api import Hp7Api

_LOGGER = logging.getLogger(__name__)

def _dig(data: dict, path: str, default=None):
    cur = data
    for p in path.split("."):
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur

def flatten_device_data(raw: dict) -> dict:
    """Appiattisce il dizionario camera EZVIZ in un formato più compatto per Home Assistant."""

    wifi_info = raw.get("WIFI", {}) or raw.get("wifiInfos", {})

    return {
        "name": raw.get("name"),
        "version": raw.get("version"),
        "status": raw.get("status"),

        "ssid": wifi_info.get("ssid"),
        "signal": wifi_info.get("signal"),
        "local_ip": raw.get("local_ip"),
        "wan_ip": raw.get("wan_ip"),

        "last_alarm_time": raw.get("last_alarm_time"),
        "last_alarm_type_name": raw.get("last_alarm_type_name"),
        "last_alarm_pic": raw.get("last_alarm_pic") or raw.get("last_snapshot"),
        "motion": raw.get("motion") or raw.get("Motion_Trigger"),
        "pir_status": raw.get("pir_status") or raw.get("PIR_Status"),
        "seconds_last_trigger": raw.get("Seconds_Last_Trigger"),

        "device_category": raw.get("device_category"),
        "device_sub_category": raw.get("device_sub_category"),
        "cam_timezone": raw.get("cam_timezone"),
        "supported_channels": raw.get("supported_channels"),

        "battery_camera_work_mode": raw.get("battery_camera_work_mode"),
        "alarm_light_luminance": raw.get("alarm_light_luminance"),
        "night_vision_model": raw.get("NightVision_Model"),
        "alarm_notify": raw.get("alarm_notify"),
        "alarm_schedules_enabled": raw.get("alarm_schedules_enabled"),

        "disk_capacity": raw.get("diskCapacity"),
        "disk_num": _dig(raw, "STATUS.diskNum"),
        "disk_state": _dig(raw, "STATUS.diskState"),

        "resource_id": raw.get("resouceid"),
        "mac_address": raw.get("mac_address"),
    }

def _convert_timestamp(ts) -> datetime | None:
    if not ts:
        return None
    try:
        from datetime import datetime, timezone
        return datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
    except Exception:
        return None


class Hp7Coordinator(DataUpdateCoordinator):
    def __init__(self, hass, api: Hp7Api, serial: str):
        super().__init__(
            hass,
            _LOGGER,
            name="EZVIZ HP7",
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SEC),
        )
        self.api = api
        self.serial = serial

    async def _async_update_data(self):
        raw = await self.hass.async_add_executor_job(self.api.get_status, self.serial)
        return flatten_device_data(raw)
