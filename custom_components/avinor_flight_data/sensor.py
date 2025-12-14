from __future__ import annotations

from typing import Any, Dict

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.sensor import SensorStateClass

from .const import (
    DOMAIN,
    CONF_AIRPORT,
    CONF_DIRECTION,
    CONF_TIME_FROM,
    CONF_TIME_TO,
    CONF_FLIGHT_TYPE,
)


def _compact_flight(flight: dict[str, Any]) -> dict[str, Any]:
    """Return a small, HA-friendly representation of a flight.

    Keeps the full `flights` attribute untouched, but provides a compact list
    for dashboards and templates.
    """
    return {
        "flightId": flight.get("flightId"),
        "airline": flight.get("airline"),
        "schedule_time": flight.get("schedule_time"),
        "arr_dep": flight.get("arr_dep"),
        "airport": flight.get("airport"),
        "status_code": flight.get("status_code"),
        "gate": flight.get("gate"),
        "check_in": flight.get("check_in"),
        "dom_int": flight.get("dom_int"),
    }


def _apply_flight_type_filter(flights: list[dict[str, Any]], flight_type: str | None) -> list[dict[str, Any]]:
    """Filter a flight list by Avinor's `dom_int` field.

    Implemented at the entity level to avoid affecting other entities that may
    share the same coordinator data.
    """
    ft = (flight_type or "").strip().upper()
    if not ft:
        return flights
    out: list[dict[str, Any]] = []
    for flight in flights:
        dom_int = str(flight.get("dom_int") or "").strip().upper()
        if dom_int == ft:
            out.append(flight)
    return out


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]

    async_add_entities([AvinorFlightsSensor(entry, coordinator)])


class AvinorFlightsSensor(CoordinatorEntity, SensorEntity):
    _attr_icon = "mdi:airplane"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, entry: ConfigEntry, coordinator) -> None:
        super().__init__(coordinator)
        self._entry = entry
        conf = entry.data
        airport = conf[CONF_AIRPORT]
        direction = conf[CONF_DIRECTION]
        flight_type = (conf.get(CONF_FLIGHT_TYPE) or "").strip().upper() or "ALL"

        # Include flight_type so multiple entities can exist for same airport/direction.
        self._attr_unique_id = f"avinor_{airport}_{direction}_{flight_type}"
        name_suffix = "All" if flight_type == "ALL" else flight_type
        self._attr_name = f"Avinor {airport} {direction} {name_suffix}"

    @property
    def device_info(self):
        conf = {**self._entry.data, **self._entry.options}
        airport = conf.get(CONF_AIRPORT)
        return {
            "identifiers": {(DOMAIN, f"device_{airport}")},
            "name": f"Avinor {airport}",
            "manufacturer": "Avinor",
            "entry_type": DeviceEntryType.SERVICE,
        }

    @property
    def native_value(self) -> Any:
        conf: Dict[str, Any] = {**self._entry.data, **self._entry.options}
        flights = self.coordinator.data.get("flights", []) if self.coordinator.data else []
        flights = _apply_flight_type_filter(flights, conf.get(CONF_FLIGHT_TYPE))
        return len(flights)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        conf: Dict[str, Any] = {**self._entry.data, **self._entry.options}
        data = self.coordinator.data or {}
        flights = _apply_flight_type_filter(data.get("flights", []), conf.get(CONF_FLIGHT_TYPE))
        compact_max = 10
        flights_summary = [_compact_flight(f) for f in flights[:compact_max]]
        return {
            "airport": conf.get(CONF_AIRPORT),
            "direction": conf.get(CONF_DIRECTION),
            "flight_type": conf.get(CONF_FLIGHT_TYPE),
            "time_from": conf.get(CONF_TIME_FROM),
            "time_to": conf.get(CONF_TIME_TO),
            "last_update": data.get("lastUpdate"),
            "flights": flights,
            "flights_summary": flights_summary,
            "flights_summary_max": compact_max,
        }

    @property
    def should_poll(self) -> bool:
        return False
