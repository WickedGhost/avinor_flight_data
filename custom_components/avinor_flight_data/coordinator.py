from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any, Dict, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AvinorApiClient
from .const import (
    CONF_AIRPORT,
    CONF_DIRECTION,
    CONF_TIME_FROM,
    CONF_TIME_TO,
    CONF_FLIGHT_TYPE,
)

_LOGGER = logging.getLogger(__name__)


def _apply_flight_type_filter(flights: list[dict[str, Any]], flight_type: str | None) -> list[dict[str, Any]]:
    ft = (flight_type or "").strip().upper()
    if not ft:
        return flights
    out: list[dict[str, Any]] = []
    for flight in flights:
        dom_int = str(flight.get("dom_int") or "").strip().upper()
        if dom_int == ft:
            out.append(flight)
    return out


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
        self._last_data: Optional[Dict[str, Any]] = None

    async def _async_update_data(self) -> Dict[str, Any]:
        try:
            flights = await self._api.async_get_flights(
                airport=self._conf[CONF_AIRPORT],
                direction=self._conf.get(CONF_DIRECTION),
                time_from=self._conf.get(CONF_TIME_FROM),
                time_to=self._conf.get(CONF_TIME_TO),
            )

            flights["flights"] = _apply_flight_type_filter(
                flights.get("flights", []),
                self._conf.get(CONF_FLIGHT_TYPE),
            )

            # Keep a copy as last known good data
            self._last_data = flights
            return flights
        except Exception as err:  # noqa: BLE001
            # Graceful fallback: if we have previous data, keep entity available with stale data.
            if self._last_data is not None:
                _LOGGER.warning("Avinor update failed, serving cached data: %s", err)
                return self._last_data
            # First update and no cache: return an empty dataset instead of making entity unavailable
            _LOGGER.error("Avinor initial update failed, returning empty dataset: %s", err)
            return {"lastUpdate": None, "flights": []}
