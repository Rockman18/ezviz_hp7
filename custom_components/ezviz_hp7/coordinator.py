from __future__ import annotations
import logging
from datetime import timedelta, datetime
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .const import UPDATE_INTERVAL_SEC
from .api import Hp7Api

_LOGGER = logging.getLogger(__name__)

class Hp7Coordinator(DataUpdateCoordinator):
    """Gestisce l'aggiornamento periodico dei dati EZVIZ HP7."""

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
        """Richiede i dati più recenti dall’API."""
        return await self.hass.async_add_executor_job(self.api.get_status, self.serial)

