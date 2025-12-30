from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

import aiohttp
import async_timeout
import xmltodict

from .const import API_BASE, API_FLIGHTS, API_AIRPORTS, AIRLABS_API_BASE, AIRLABS_API_FLIGHT_DETAILS

_LOGGER = logging.getLogger(__name__)


class AvinorApiClient:
    """Simple async client for Avinor XML feeds."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def _get_xml(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            _LOGGER.debug("Avinor request: url=%s params=%s", url, params)
            async with async_timeout.timeout(30):
                async with self._session.get(
                    url,
                    params=params,
                    headers={"Accept": "application/xml"},
                ) as resp:
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
            f"{API_BASE}/airportNames",  # non-versioned variant
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
        
        # Parse airport list - structure: airportNames -> airportName (list)
        airports = []
        try:
            # Try new structure: <airportNames><airportName code="..." name="..."/></airportNames>
            items = data.get("airportNames", {}).get("airportName", [])
            if not items:
                # Try old structure: <airports><airport iata="..." name="..."/></airports>
                items = data.get("airports", {}).get("airport", [])
            
            if isinstance(items, dict):
                items = [items]
            
            for it in items:
                # Try multiple field names for IATA code
                iata = it.get("@code") or it.get("code") or it.get("@iata") or it.get("iata")
                name = it.get("@name") or it.get("name") or iata
                if iata and len(iata) == 3:  # Valid IATA codes are 3 letters
                    airports.append({"iata": iata.upper(), "name": name})
            
            _LOGGER.debug("Parsed %d airports from XML", len(airports))
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Failed parsing airport XML: %s", err, exc_info=True)
        
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
            # Debug log first flight to see structure
            if len(result["flights"]) == 0:
                _LOGGER.debug("First flight raw data keys: %s", list(it.keys()))
                _LOGGER.debug("First flight sample: %s", {k: it.get(k) for k in list(it.keys())[:10]})
            
            # Normalize fields we care about
            status = it.get("status", {}) or {}
            status_code = status.get("@code") if isinstance(status, dict) else None
            
            # Extract flight ID - Avinor uses flight_id (with underscore)
            flight_id = it.get("flight_id") or it.get("flightId") or ""
            
            result["flights"].append(
                {
                    "uniqueId": it.get("@uniqueId"),
                    "airline": it.get("airline"),
                    "flightId": flight_id,
                    "dom_int": it.get("dom_int"),
                    "schedule_time": it.get("schedule_time"),
                    "arr_dep": it.get("arr_dep"),
                    "airport": it.get("airport"),
                    "check_in": it.get("check_in"),
                    "gate": it.get("gate"),
                    "status_code": status_code,
                    "status_time": status.get("@time") if isinstance(status, dict) else None,
                }
            )
        return result


class AirlabsApiClient:
    """Simple async client for Airlabs Flight API (JSON)."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def _get_json(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            _LOGGER.debug("Airlabs request: url=%s params=%s", url, {k: v for k, v in (params or {}).items() if k != "api_key"})
            async with async_timeout.timeout(30):
                async with self._session.get(
                    url,
                    params=params,
                    headers={"Accept": "application/json"},
                ) as resp:
                    resp.raise_for_status()
                    return await resp.json(content_type=None)
        except asyncio.TimeoutError as err:
            _LOGGER.error("Airlabs API timeout fetching %s: %s", url, err)
            raise
        except aiohttp.ClientResponseError as err:
            _LOGGER.error("Airlabs API HTTP error (%s) for %s: %s", err.status, url, err)
            raise
        except aiohttp.ClientConnectionError as err:
            _LOGGER.error("Airlabs API connection error for %s: %s", url, err)
            raise
        except aiohttp.ClientError as err:
            _LOGGER.error("Airlabs API client error for %s: %s", url, err)
            raise

    async def async_get_flight_details(
        self,
        *,
        api_key: str,
        flight_iata: str | None = None,
        flight_icao: str | None = None,
        flight_number: str | None = None,
    ) -> Dict[str, Any]:
        """Fetch details for a specific flight using Airlabs.

        Uses https://airlabs.co/docs/flight

        One of `flight_iata`, `flight_icao`, or `flight_number` must be provided.
        Returns the `response` object from Airlabs (or an empty dict if none).
        """

        if not api_key or not str(api_key).strip():
            raise ValueError("api_key is required")

        flight_iata = (flight_iata or "").strip() or None
        flight_icao = (flight_icao or "").strip() or None
        flight_number = (flight_number or "").strip() or None

        if not (flight_iata or flight_icao or flight_number):
            raise ValueError("One of flight_iata, flight_icao, flight_number is required")

        params: Dict[str, Any] = {"api_key": api_key}
        if flight_iata:
            params["flight_iata"] = flight_iata
        if flight_icao:
            params["flight_icao"] = flight_icao
        if flight_number:
            params["flight_number"] = flight_number

        url = f"{AIRLABS_API_BASE}{AIRLABS_API_FLIGHT_DETAILS}"
        payload = await self._get_json(url, params=params)

        # Airlabs typically returns {"request": ..., "response": ..., "error": ...}
        if isinstance(payload, dict) and payload.get("error"):
            message = payload.get("message") or payload.get("error")
            raise RuntimeError(f"Airlabs API error: {message}")

        if isinstance(payload, dict) and "response" in payload:
            response = payload.get("response")
            return response if isinstance(response, dict) else {"response": response}

        return payload if isinstance(payload, dict) else {"response": payload}
