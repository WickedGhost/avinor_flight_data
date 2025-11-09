from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

import aiohttp
import async_timeout
import xmltodict

from .const import API_BASE, API_FLIGHTS, API_AIRPORTS

_LOGGER = logging.getLogger(__name__)


class AvinorApiClient:
    """Simple async client for Avinor XML feeds."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def _get_xml(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            async with async_timeout.timeout(30):
                async with self._session.get(url, params=params) as resp:
                    resp.raise_for_status()
                    text = await resp.text()
                    return xmltodict.parse(text)
        except asyncio.TimeoutError as err:
            _LOGGER.error("Avinor API timeout fetching %s: %s", url, err)
            raise
        except aiohttp.ClientResponseError as err:
            _LOGGER.error("Avinor API HTTP error (%s) for %s: %s", err.status, url, err)
            raise
        except aiohttp.ClientConnectionError as err:
            _LOGGER.error("Avinor API connection error for %s: %s", url, err)
            raise
        except aiohttp.ClientError as err:
            _LOGGER.error("Avinor API client error for %s: %s", url, err)
            raise

    async def async_get_airports(self) -> List[Dict[str, str]]:
        """Fetch airport names and IATA codes.

        Returns a list of dicts: {"iata": "OSL", "name": "Oslo Lufthavn"}
        """
        primary_url = f"{API_BASE}{API_AIRPORTS}"
        alt_urls = [
            primary_url.rstrip("/") + "/",  # ensure trailing slash variant
            f"{API_BASE}{API_AIRPORTS.split('/')[0]}",  # extremely defensive: first segment only
        ]
        data = None
        last_err: Exception | None = None
        for url in [primary_url] + alt_urls:
            try:
                data = await self._get_xml(url)
                break
            except aiohttp.ClientResponseError as err:  # specific HTTP errors
                last_err = err
                if err.status == 404:
                    _LOGGER.warning("Airport endpoint 404 at %s, trying fallback variant", url)
                    continue
                raise
            except Exception as err:  # noqa: BLE001
                last_err = err
                _LOGGER.debug("Airport fetch attempt failed at %s: %s", url, err)
                continue
        if data is None:
            _LOGGER.error("All airport endpoint attempts failed: %s", last_err)
            return []
        # Structure: airports -> airport (list of entries)
        airports = []
        try:
            items = data.get("airports", {}).get("airport", [])
            if isinstance(items, dict):
                items = [items]
            for it in items:
                iata = it.get("@iata") or it.get("iata") or it.get("code")
                name = it.get("name") or it.get("@name") or iata
                if iata:
                    airports.append({"iata": iata, "name": name})
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Unexpected airport XML format: %s", err)
        # Sort by IATA code
        airports.sort(key=lambda a: a.get("iata", ""))
        return airports

    async def async_get_flights(
        self,
        *,
        airport: str,
        direction: Optional[str] = None,
        time_from: Optional[int] = None,
        time_to: Optional[int] = None,
        codeshare: bool = False,
    ) -> Dict[str, Any]:
        """Fetch flights for an airport with optional filtering.

        Returns a dict with keys: lastUpdate, flights (list)
        """
        params: Dict[str, Any] = {
            "airport": airport,
        }
        if direction:
            params["direction"] = direction
        if time_from is not None:
            params["TimeFrom"] = int(time_from)
        if time_to is not None:
            params["TimeTo"] = int(time_to)
        if codeshare:
            params["codeshare"] = "Y"

        url = f"{API_BASE}{API_FLIGHTS}"
        data = await self._get_xml(url, params=params)

        flights_node = data.get("airport", {}).get("flights", {})
        result: Dict[str, Any] = {
            "lastUpdate": flights_node.get("@lastUpdate"),
            "flights": [],
        }
        items = flights_node.get("flight", [])
        if isinstance(items, dict):
            items = [items]
        for it in items:
            # Normalize fields we care about
            status = it.get("status", {}) or {}
            status_code = status.get("@code") if isinstance(status, dict) else None
            result["flights"].append(
                {
                    "uniqueId": it.get("@uniqueId"),
                    "flightId": it.get("flightId"),
                    "dom_int": it.get("dom_int"),
                    "schedule_time": it.get("schedule_time"),
                    "arr_dep": it.get("arr_dep"),
                    "airport": it.get("airport"),
                    "check_in": it.get("check_in"),
                    "gate": it.get("gate"),
                    "status_code": status_code,
                }
            )
        return result
