from __future__ import annotations

"""Avinor Flight Data integration setup.

Handles creation and lifecycle of coordinators per config entry.
"""

from datetime import timedelta
import logging
from typing import TypedDict

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, PLATFORMS, UPDATE_INTERVAL_SECONDS, CONF_AIRLABS_API_KEY, SERVICE_GET_FLIGHT_DETAILS
from .coordinator import AvinorCoordinator
from .api import AvinorApiClient, AirlabsApiClient

_LOGGER = logging.getLogger(__name__)


AvinorConfigEntry = ConfigEntry  # type alias for clarity


class DomainData(TypedDict):
    coordinator: AvinorCoordinator
    api: AvinorApiClient


def _async_register_services(hass: HomeAssistant) -> None:
    """Register domain services once."""

    domain_store = hass.data.setdefault(DOMAIN, {})
    if domain_store.get("services_registered"):
        return

    schema = vol.Schema(
        {
            vol.Optional("config_entry_id"): vol.Coerce(str),
            vol.Optional("api_key"): vol.Coerce(str),
            vol.Optional("flight_iata"): vol.Coerce(str),
            vol.Optional("flight_icao"): vol.Coerce(str),
            vol.Optional("flight_number"): vol.Coerce(str),
        }
    )

    async def _handle_get_flight_details(call):
        config_entry_id = call.data.get("config_entry_id")
        api_key = call.data.get("api_key")

        flight_iata = call.data.get("flight_iata")
        flight_icao = call.data.get("flight_icao")
        flight_number = call.data.get("flight_number")

        if not api_key:
            # Find an entry holding an Airlabs key.
            entries = hass.config_entries.async_entries(DOMAIN)
            if config_entry_id:
                entries = [e for e in entries if e.entry_id == config_entry_id]

            for entry in entries:
                conf = {**entry.data, **entry.options}
                key = conf.get(CONF_AIRLABS_API_KEY)
                if key:
                    api_key = key
                    break

        if not api_key:
            raise HomeAssistantError(
                "No Airlabs API key configured. Add it in the integration options, or pass api_key in the service call."
            )

        session = async_get_clientsession(hass)
        client = AirlabsApiClient(session)
        try:
            details = await client.async_get_flight_details(
                api_key=api_key,
                flight_iata=flight_iata,
                flight_icao=flight_icao,
                flight_number=flight_number,
            )
        except ValueError as err:
            raise HomeAssistantError(str(err)) from err
        except RuntimeError as err:
            raise HomeAssistantError(str(err)) from err

        # Always store last result for convenience/debugging.
        domain_store["last_flight_details"] = details
        return details

    # Prefer returning a response payload when HA supports it.
    try:
        from homeassistant.core import SupportsResponse  # type: ignore

        try:
            hass.services.async_register(
                DOMAIN,
                SERVICE_GET_FLIGHT_DETAILS,
                _handle_get_flight_details,
                schema=schema,
                supports_response=SupportsResponse.ONLY,
            )
        except TypeError:
            hass.services.async_register(
                DOMAIN,
                SERVICE_GET_FLIGHT_DETAILS,
                _handle_get_flight_details,
                schema=schema,
            )
    except Exception:  # noqa: BLE001
        hass.services.async_register(
            DOMAIN,
            SERVICE_GET_FLIGHT_DETAILS,
            _handle_get_flight_details,
            schema=schema,
        )

    domain_store["services_registered"] = True


async def async_setup_entry(hass: HomeAssistant, entry: AvinorConfigEntry) -> bool:
    """Set up Avinor Flight Data from a config entry."""
    session = async_get_clientsession(hass)
    api = AvinorApiClient(session)

    # Merge options over data so updated options take effect on reloads
    conf = {**entry.data, **entry.options}

    coordinator = AvinorCoordinator(
        hass,
        api,
        conf,
        update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = DomainData(
        coordinator=coordinator,
        api=api,
    )

    _async_register_services(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: AvinorConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

        # Remove services when the last entry is unloaded.
        if not hass.config_entries.async_entries(DOMAIN):
            try:
                hass.services.async_remove(DOMAIN, SERVICE_GET_FLIGHT_DETAILS)
            except Exception:  # noqa: BLE001
                pass
            hass.data[DOMAIN].pop("services_registered", None)
    return unload_ok


async def async_update_listener(hass: HomeAssistant, entry: AvinorConfigEntry) -> None:
    """Handle options update: reload the entry."""
    await hass.config_entries.async_reload(entry.entry_id)
