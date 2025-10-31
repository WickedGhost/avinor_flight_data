from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any, Dict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AvinorApiClient
from .const import (
    CONF_AIRPORT,
    CONF_DIRECTION,
    CONF_TIME_FROM,
    CONF_TIME_TO,
)

_LOGGER = logging.getLogger(__name__)


class AvinorCoordinator(DataUpdateCoordinator[Dict[str, Any]]):
    """Coordinator to manage fetching Avinor flight data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: AvinorApiClient,
        conf: Dict[str, Any],
        *,
        update_interval: timedelta,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Avinor Flight Data",
            update_interval=update_interval,
        )
        self._api = api
        self._conf = conf

    async def _async_update_data(self) -> Dict[str, Any]:
        try:
            flights = await self._api.async_get_flights(
                airport=self._conf[CONF_AIRPORT],
                direction=self._conf.get(CONF_DIRECTION),
                time_from=self._conf.get(CONF_TIME_FROM),
                time_to=self._conf.get(CONF_TIME_TO),
            )
            return flights
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(str(err)) from err
