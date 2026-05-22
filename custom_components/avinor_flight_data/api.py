from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import aiohttp
import async_timeout
import xmltodict

from .const import (
    API_BASE,
    API_FLIGHTS,
    API_AIRPORTS,
    AIRLABS_API_BASE,
    AIRLABS_API_AIRPORTS,
    AIRLABS_API_FLIGHT_DETAILS,
    AIRLABS_API_SCHEDULES,
)

_LOGGER = logging.getLogger(__name__)

NORWAY_COUNTRY_CODE = "NO"
SCHENGEN_COUNTRY_CODES = {
    "AT", "BE", "CH", "CZ", "DE", "DK", "EE", "ES", "FI", "FR", "GR", "HR",
    "HU", "IS", "IT", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "SE", "SI", "SK",
}


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
        self._airport_cache: dict[str, dict[str, Any]] = {}

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

    async def async_get_airport(self, *, api_key: str, iata_code: str) -> Dict[str, Any]:
        """Fetch airport metadata for one IATA code using Airlabs."""

        code = (iata_code or "").strip().upper()
        if not code:
            return {}
        if code in self._airport_cache:
            return self._airport_cache[code]

        payload = await self._get_json(
            f"{AIRLABS_API_BASE}{AIRLABS_API_AIRPORTS}",
            params={"api_key": api_key, "iata_code": code},
        )
        response = payload.get("response") if isinstance(payload, dict) else None
        if isinstance(response, list):
            airport = response[0] if response else {}
        elif isinstance(response, dict):
            airport = response
        else:
            airport = {}
        self._airport_cache[code] = airport
        return airport

    async def async_get_schedules(
        self,
        *,
        api_key: str,
        airport: str,
        direction: Optional[str] = None,
        time_from: Optional[int] = None,
        time_to: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Fetch airport schedules from Airlabs and normalize them to integration flight records."""

        if not api_key or not str(api_key).strip():
            raise ValueError("api_key is required")

        airport = (airport or "").strip().upper()
        direction = (direction or "A").strip().upper() or "A"

        params: Dict[str, Any] = {
            "api_key": api_key,
            "limit": 50,
        }
        if direction == "D":
            params["dep_iata"] = airport
        else:
            params["arr_iata"] = airport

        payload = await self._get_json(f"{AIRLABS_API_BASE}{AIRLABS_API_SCHEDULES}", params=params)
        if isinstance(payload, dict) and payload.get("error"):
            message = payload.get("message") or payload.get("error")
            raise RuntimeError(f"Airlabs API error: {message}")

        response = payload.get("response") if isinstance(payload, dict) else None
        rows = response if isinstance(response, list) else []
        rows = self._filter_schedule_rows(rows, direction=direction, time_from=time_from, time_to=time_to)
        flights = await self._normalize_schedule_rows(api_key=api_key, rows=rows, direction=direction, airport=airport)
        return {
            "lastUpdate": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "flights": flights,
        }

    def _filter_schedule_rows(
        self,
        rows: List[Dict[str, Any]],
        *,
        direction: str,
        time_from: Optional[int],
        time_to: Optional[int],
    ) -> List[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(hours=max(int(time_from or 0), 0))
        window_end = now + timedelta(hours=max(int(time_to or 0), 0))
        filtered: List[Dict[str, Any]] = []
        for row in rows:
            schedule_time = self._parse_schedule_datetime(row, direction)
            if schedule_time is None:
                continue
            if schedule_time < window_start or schedule_time > window_end:
                continue
            filtered.append(row)
        return filtered

    async def _normalize_schedule_rows(
        self,
        *,
        api_key: str,
        rows: List[Dict[str, Any]],
        direction: str,
        airport: str,
    ) -> List[Dict[str, Any]]:
        deduped = self._dedupe_schedule_rows(rows)
        opposite_codes = {
            self._get_counterparty_airport(row, direction)
            for row in deduped
            if self._get_counterparty_airport(row, direction)
        }
        airport_meta: dict[str, dict[str, Any]] = {}
        for code in opposite_codes:
            airport_meta[code] = await self.async_get_airport(api_key=api_key, iata_code=code)

        flights: List[Dict[str, Any]] = []
        for row in deduped:
            other_airport = self._get_counterparty_airport(row, direction)
            meta = airport_meta.get(other_airport or "", {})
            flights.append(
                {
                    "uniqueId": self._schedule_identity(row),
                    "airline": row.get("airline_iata") or row.get("airline_icao"),
                    "flightId": row.get("flight_iata") or row.get("flight_icao") or row.get("flight_number") or "",
                    "dom_int": self._classify_airlabs_flight(country_code=str(meta.get("country_code") or "").upper(), airport_code=other_airport),
                    "schedule_time": self._schedule_time_utc(row, direction),
                    "arr_dep": direction,
                    "airport": other_airport,
                    "check_in": row.get("dep_gate") if direction == "D" else None,
                    "gate": row.get("arr_gate") if direction == "A" else row.get("dep_gate"),
                    "status_code": self._map_airlabs_status(row.get("status")),
                    "status_time": row.get("arr_actual_utc") if direction == "A" else row.get("dep_actual_utc"),
                }
            )
        return flights

    def _dedupe_schedule_rows(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        grouped: dict[str, Dict[str, Any]] = {}
        for row in rows:
            key = self._schedule_identity(row)
            current = grouped.get(key)
            if current is None or self._schedule_preference(row) > self._schedule_preference(current):
                grouped[key] = row
        return list(grouped.values())

    def _schedule_identity(self, row: Dict[str, Any]) -> str:
        return "|".join(
            [
                str(row.get("cs_flight_iata") or row.get("cs_flight_icao") or row.get("flight_iata") or row.get("flight_icao") or row.get("flight_number") or ""),
                str(row.get("dep_iata") or row.get("dep_icao") or ""),
                str(row.get("arr_iata") or row.get("arr_icao") or ""),
                str(row.get("dep_time_utc") or ""),
                str(row.get("arr_time_utc") or ""),
            ]
        )

    def _schedule_preference(self, row: Dict[str, Any]) -> int:
        score = 0
        if not row.get("cs_flight_iata") and not row.get("cs_flight_icao"):
            score += 10
        if row.get("flight_iata"):
            score += 2
        if row.get("arr_estimated_utc") or row.get("dep_estimated_utc"):
            score += 1
        return score

    def _get_counterparty_airport(self, row: Dict[str, Any], direction: str) -> str:
        if direction == "D":
            return str(row.get("arr_iata") or row.get("arr_icao") or "").strip().upper()
        return str(row.get("dep_iata") or row.get("dep_icao") or "").strip().upper()

    def _schedule_time_utc(self, row: Dict[str, Any], direction: str) -> str:
        if direction == "D":
            return str(row.get("dep_time_utc") or row.get("dep_estimated_utc") or row.get("dep_time") or "")
        return str(row.get("arr_time_utc") or row.get("arr_estimated_utc") or row.get("arr_time") or "")

    def _parse_schedule_datetime(self, row: Dict[str, Any], direction: str) -> datetime | None:
        raw = self._schedule_time_utc(row, direction)
        if not raw:
            return None
        text = raw.strip().replace(" ", "T")
        if text.endswith("Z"):
            parsed = text
        elif "T" in text:
            parsed = f"{text}Z"
        else:
            parsed = text
        try:
            return datetime.fromisoformat(parsed.replace("Z", "+00:00"))
        except ValueError:
            return None

    def _classify_airlabs_flight(self, *, country_code: str, airport_code: str | None) -> str:
        if not airport_code:
            return ""
        if country_code == NORWAY_COUNTRY_CODE:
            return "D"
        if country_code in SCHENGEN_COUNTRY_CODES:
            return "S"
        if country_code:
            return "I"
        return ""

    def _map_airlabs_status(self, status: Any) -> str:
        normalized = str(status or "").strip().lower()
        return {
            "scheduled": "E",
            "active": "EXP",
            "en-route": "EXP",
            "landed": "A",
            "cancelled": "C",
        }.get(normalized, str(status or "").strip().upper())
