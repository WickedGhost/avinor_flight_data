from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    CONF_AIRPORT,
    CONF_DIRECTION,
    CONF_TIME_FROM,
    CONF_TIME_TO,
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]

    async_add_entities([AvinorFlightsSensor(entry, coordinator)])


class AvinorFlightsSensor(CoordinatorEntity, SensorEntity):
    _attr_icon = "mdi:airplane"

    def __init__(self, entry: ConfigEntry, coordinator) -> None:
        super().__init__(coordinator)
        self._entry = entry
        conf = entry.data
        airport = conf[CONF_AIRPORT]
        direction = conf[CONF_DIRECTION]
        self._attr_unique_id = f"avinor_{airport}_{direction}"
        self._attr_name = f"Avinor {airport} {direction}"

    @property
    def device_info(self):
        conf = self._entry.data
        airport = conf[CONF_AIRPORT]
        return {
            "identifiers": {(DOMAIN, f"device_{airport}")},
            "name": f"Avinor {airport}",
            "manufacturer": "Avinor",
            "entry_type": DeviceEntryType.SERVICE,
        }

    @property
    def native_value(self) -> Any:
        flights = self.coordinator.data.get("flights", []) if self.coordinator.data else []
        return len(flights)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        conf = self._entry.data
        data = self.coordinator.data or {}
        return {
            "airport": conf.get(CONF_AIRPORT),
            "direction": conf.get(CONF_DIRECTION),
            "time_from": conf.get(CONF_TIME_FROM),
            "time_to": conf.get(CONF_TIME_TO),
            "last_update": data.get("lastUpdate"),
            "flights": data.get("flights", []),
        }

    @property
    def should_poll(self) -> bool:
        return False
