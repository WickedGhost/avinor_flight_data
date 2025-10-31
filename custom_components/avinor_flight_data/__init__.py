from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    PLATFORMS,
    UPDATE_INTERVAL_SECONDS,
)
from .coordinator import AvinorCoordinator
from .api import AvinorApiClient

_LOGGER = logging.getLogger(__name__)


type AvinorConfigEntry = ConfigEntry


async def async_setup_entry(hass: HomeAssistant, entry: AvinorConfigEntry) -> bool:
    """Set up Avinor Flight Data from a config entry."""
    session = async_get_clientsession(hass)
    api = AvinorApiClient(session)

    coordinator = AvinorCoordinator(
        hass,
        api,
        entry.data,
        update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "api": api,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: AvinorConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_update_listener(hass: HomeAssistant, entry: AvinorConfigEntry) -> None:
    """Handle options update: reload the entry."""
    await hass.config_entries.async_reload(entry.entry_id)
