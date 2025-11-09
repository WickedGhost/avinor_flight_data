from __future__ import annotations

import time
import logging
from typing import Any, Dict, List

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    selector,
)

from .const import (
    DOMAIN,
    CONF_AIRPORT,
    CONF_DIRECTION,
    CONF_TIME_FROM,
    CONF_TIME_TO,
    DEFAULT_TIME_FROM,
    DEFAULT_TIME_TO,
)
from .api import AvinorApiClient

_LOGGER = logging.getLogger(__name__)


class AvinorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Avinor Flight Data."""

    VERSION = 1

    async def async_step_user(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        errors: Dict[str, str] = {}

        if user_input is not None:
            # Unique key: airport + direction
            await self.async_set_unique_id(f"{user_input[CONF_AIRPORT]}_{user_input[CONF_DIRECTION]}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=f"{user_input[CONF_AIRPORT]} {user_input[CONF_DIRECTION]}", data=user_input)

        airports = await _async_fetch_airports(self.hass)

        if airports:
            options = [
                SelectOptionDict(value=a["iata"], label=f"{a['iata']} - {a['name']}")
                for a in airports
            ]
            airport_selector = selector(
                SelectSelector(
                    SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN)
                )
            )
        else:
            # Allow manual 3-letter IATA input as a safe fallback
            # Using a text selector here would be ideal, but voluptuous schema will accept string
            airport_selector = str

        data_schema = vol.Schema(
            {
                vol.Required(CONF_AIRPORT): airport_selector,
                vol.Required(CONF_DIRECTION, default="A"): selector(
                    SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(value="A", label="A (Arrivals)"),
                                SelectOptionDict(value="D", label="D (Departures)"),
                            ],
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    )
                ),
                vol.Optional(CONF_TIME_FROM, default=DEFAULT_TIME_FROM): selector(
                    NumberSelector(NumberSelectorConfig(min=0, max=72, step=1, mode=NumberSelectorMode.BOX))
                ),
                vol.Optional(CONF_TIME_TO, default=DEFAULT_TIME_TO): selector(
                    NumberSelector(NumberSelectorConfig(min=0, max=72, step=1, mode=NumberSelectorMode.BOX))
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={"airport_count": str(len(airports))},
        )

    async def async_step_import(self, data: Dict[str, Any]) -> FlowResult:
        """Handle import from YAML if ever added."""
        return await self.async_step_user(data)

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        return AvinorOptionsFlow(config_entry)


class AvinorOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        hass: HomeAssistant = self.hass
        airports = await _async_fetch_airports(hass)

        current = {**self.config_entry.data, **self.config_entry.options}
        airport_default = current.get(CONF_AIRPORT)
        direction_default = current.get(CONF_DIRECTION, "A")
        time_from_default = current.get(CONF_TIME_FROM)
        time_to_default = current.get(CONF_TIME_TO)

        if airports:
            options = [
                SelectOptionDict(value=a["iata"], label=f"{a['iata']} - {a['name']}")
                for a in airports
            ]
            airport_selector = selector(
                SelectSelector(
                    SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN)
                )
            )
        else:
            airport_selector = str

        data_schema = vol.Schema(
            {
                vol.Optional(CONF_AIRPORT, default=airport_default): airport_selector,
                vol.Optional(CONF_DIRECTION, default=direction_default): selector(
                    SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(value="A", label="A (Arrivals)"),
                                SelectOptionDict(value="D", label="D (Departures)"),
                            ],
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    )
                ),
                vol.Optional(CONF_TIME_FROM, default=time_from_default): selector(
                    NumberSelector(NumberSelectorConfig(min=0, max=72, step=1, mode=NumberSelectorMode.BOX))
                ),
                vol.Optional(CONF_TIME_TO, default=time_to_default): selector(
                    NumberSelector(NumberSelectorConfig(min=0, max=72, step=1, mode=NumberSelectorMode.BOX))
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=data_schema)


async def _async_fetch_airports(hass: HomeAssistant) -> List[Dict[str, str]]:
    # cache airports for 1 day to reduce setup-time API calls
    domain_store = hass.data.setdefault(DOMAIN, {})
    cache = domain_store.get("airports_cache")
    now = time.time()
    if cache and isinstance(cache, dict) and (now - cache.get("ts", 0)) < 24 * 3600:
        airports = cache.get("data", [])
        if airports:
            return airports

    session = async_get_clientsession(hass)
    api = AvinorApiClient(session)
    try:
        airports = await api.async_get_airports()
        if not airports:
            # Ensure we always have a few options
            airports = [
                {"iata": "OSL", "name": "Oslo Lufthavn"},
                {"iata": "BGO", "name": "Bergen Lufthavn"},
                {"iata": "TRD", "name": "Trondheim Lufthavn"},
                {"iata": "SVG", "name": "Stavanger Lufthavn"},
            ]
        domain_store["airports_cache"] = {"data": airports, "ts": now}
        return airports
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("Failed fetching airports list: %s", err)
        # Fallback minimal list
        airports = [
            {"iata": "OSL", "name": "Oslo Lufthavn"},
            {"iata": "BGO", "name": "Bergen Lufthavn"},
            {"iata": "TRD", "name": "Trondheim Lufthavn"},
            {"iata": "SVG", "name": "Stavanger Lufthavn"},
        ]
        domain_store["airports_cache"] = {"data": airports, "ts": now}
        return airports
