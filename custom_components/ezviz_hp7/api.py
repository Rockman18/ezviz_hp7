import logging
from typing import Any, Dict, Optional
from .pylocalapi.client import EzvizClient
from .pylocalapi.camera import EzvizCamera

_LOGGER = logging.getLogger(__name__)

DEFAULT_DOOR_LOCK_NO = 2
DEFAULT_GATE_LOCK_NO = 1

class Hp7Api:
    def __init__(
        self,
        username: str,
        password: Optional[str] = None,
        region: str = "eu",
        token: Optional[dict] = None,
    ):
        self._username = username
        self._password = password
        self._region = region
        self._token = token
        self._client: Optional[EzvizClient] = None

        self._url = "apiieu.ezvizlife.com" if region == "eu" else "apiisa.ezvizlife.com"

        self.supports_door = True
        self.supports_gate = True

    def ensure_client(self) -> None:
        """Crea il client Ezviz se non esiste e gestisce il token."""
        if self._client:
            return

        self._client = EzvizClient(
            account=self._username,
            password=self._password,
            url=self._url,
            token=self._token,
        )

        if not self._token:
            self._login_and_store_token()

    def _login_and_store_token(self) -> None:
        """Login al server e salva il token in memoria."""
        try:
            self._token = self._client.login()
            _LOGGER.info("EZVIZ HP7: login OK, token pronto")
        except Exception as e:
            _LOGGER.error("EZVIZ HP7: login fallito: %s", e)
            raise

    def login(self) -> bool:
        """Compatibile con setup entry di Home Assistant."""
        self.ensure_client()
        return True

    def detect_capabilities(self, serial: str) -> None:
        """Rileva le capabilities del device (di default True)."""
        self.ensure_client()
        try:
            dev = self._client.get_device_infos(serial).get(serial, {})
            _LOGGER.info("EZVIZ HP7: device %s info=%s", serial, dev)
        except Exception as e:
            _LOGGER.debug("detect_capabilities fallita: %s", e)
        self.supports_door = True
        self.supports_gate = True

    def list_devices(self) -> Dict[str, Dict[str, Any]]:
        self.ensure_client()
        devices = self._client.get_device_infos()
        result: Dict[str, Dict[str, Any]] = {}
        for serial, data in devices.items():
            name = data.get("name") or data.get("deviceName") or "Device"
            result[serial] = {"device_name": name}
        return result

    def _try_unlock(self, serial: str, lock_no: int) -> bool:
        self.ensure_client()
        user_id = self._token.get("username") or self._username
        try:
            self._client.remote_unlock(serial, user_id, lock_no)
            _LOGGER.info("remote_unlock OK (serial=%s, lock_no=%s)", serial, lock_no)
            return True
        except Exception as e:
            _LOGGER.warning(
                "remote_unlock KO (serial=%s, lock_no=%s): %s", serial, lock_no, e
            )
            return False

    def unlock_door(self, serial: str) -> bool:
        return self._try_unlock(serial, DEFAULT_DOOR_LOCK_NO) or self._try_unlock(
            serial, DEFAULT_GATE_LOCK_NO
        )

    def unlock_gate(self, serial: str) -> bool:
        return self._try_unlock(serial, DEFAULT_GATE_LOCK_NO) or self._try_unlock(
            serial, DEFAULT_DOOR_LOCK_NO
        )

    def get_status(self, serial: str) -> dict:
        self.ensure_client()
        try:
            camera = EzvizCamera(self._client, serial)
            cam_status = camera.status(refresh=True)

            wifi_info = cam_status.get("WIFI", {})

            _LOGGER.info("EZVIZ HP7 RAW CAMERA JSON: %s", cam_status)
            
            return {
                "name": cam_status.get("name"), #Nome
                "version": cam_status.get("version"), #Versione firmware
                "upgrade_available": cam_status.get("upgrade_available"), #Disponibilità aggiornamneto? true/false
                "status": cam_status.get("status"), #Disponibilità aggiornamneto? true/false
                "wan_ip": cam_status.get("wan_ip"), #Indirizzo ip locale
                "pir_status": cam_status.get("PIR_Status"), #Presenza di movimento? 1/0
                "motion": cam_status.get("Motion_Trigger"), #Presenza di movimento? true/false
                "seconds_last_trigger": cam_status.get("Seconds_Last_Trigger"), #Secondi da ultimo movimento 0.0
                "last_alarm_time": cam_status.get("last_alarm_time"), #Data ultimo allarme 2025-10-17 13:51:37
                "last_alarm_pic": cam_status.get("last_alarm_pic"), #Pic ultima rilevazione
                "alarm_name": cam_status.get("last_alarm_type_name"),
                #Info Wifi
                "ssid": wifi_info.get("ssid"),
                "signal": wifi_info.get("signal"),
                "local_ip": cam_status.get("local_ip") or wifi_info.get("address"),
            }

        except Exception as e:
            _LOGGER.warning("get_status fallita per %s: %s", serial, e)
            return {}
