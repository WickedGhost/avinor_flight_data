import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import pytest

from custom_components.avinor_flight_data.api import AvinorApiClient
from custom_components.avinor_flight_data.api import AirlabsApiClient
from custom_components.avinor_flight_data.sensor import (
    AvinorFlightsSensor,
    _apply_flight_type_filter,
    _compact_flight,
)


class StubClient(AvinorApiClient):
    def __init__(self, flights_payload, airports_payload):
        # don't call super; we won't use the aiohttp session in tests
        self._flights_payload = flights_payload
        self._airports_payload = airports_payload

    async def _get_xml(self, url: str, params=None):
        if "airportNames" in url:
            return self._airports_payload
        return self._flights_payload


class StubAirlabsClient(AirlabsApiClient):
    def __init__(self, payload):
        super().__init__(session=None)
        self._payload = payload
        self.last_url = None
        self.last_params = None

    async def _get_json(self, url: str, params=None):
        self.last_url = url
        self.last_params = params
        if callable(self._payload):
            return self._payload(url, params)
        return self._payload


@pytest.mark.asyncio
async def test_async_get_flights_parsing():
    flights_payload = {
        "airport": {
            "flights": {
                "@lastUpdate": "2025-01-01T12:00:00Z",
                "flight": [
                    {
                        "@uniqueId": "u1",
                        "flightId": "DY123",
                        "dom_int": "D",
                        "schedule_time": "2025-01-01T13:00:00Z",
                        "arr_dep": "D",
                        "airport": "OSL",
                        "check_in": "1",
                        "gate": "A12",
                        "status": {"@code": "BRD"},
                    },
                    {
                        "@uniqueId": "u2",
                        "flightId": "SK456",
                        "dom_int": "I",
                        "schedule_time": "2025-01-01T14:00:00Z",
                        "arr_dep": "A",
                        "airport": "BGO",
                        "check_in": None,
                        "gate": None,
                        "status": {"@code": "EXP"},
                    },
                ],
            }
        }
    }
    airports_payload = {"airports": {"airport": {"@iata": "OSL", "name": "Oslo"}}}

    client = StubClient(flights_payload, airports_payload)
    result = await client.async_get_flights(airport="OSL", direction="A")

    assert result["lastUpdate"] == "2025-01-01T12:00:00Z"
    assert isinstance(result["flights"], list)
    assert len(result["flights"]) == 2
    assert result["flights"][0]["flightId"] == "DY123"
    assert result["flights"][0]["status_code"] == "BRD"


@pytest.mark.asyncio
async def test_async_get_airports_parsing_and_sorting():
    airports_payload = {
        "airports": {
            "airport": [
                {"@iata": "BGO", "name": "Bergen"},
                {"@iata": "OSL", "name": "Oslo"},
            ]
        }
    }
    flights_payload = {}

    client = StubClient(flights_payload, airports_payload)
    airports = await client.async_get_airports()

    assert airports == [
        {"iata": "BGO", "name": "Bergen"},
        {"iata": "OSL", "name": "Oslo"},
    ]


def test_apply_flight_type_filter():
    flights = [
        {"flightId": "SK1", "dom_int": "D"},
        {"flightId": "SK2", "dom_int": "I"},
        {"flightId": "SK3", "dom_int": "S"},
        {"flightId": "SK4", "dom_int": None},
    ]
    assert [f["flightId"] for f in _apply_flight_type_filter(flights, "")] == ["SK1", "SK2", "SK3", "SK4"]
    assert [f["flightId"] for f in _apply_flight_type_filter(flights, "D")] == ["SK1"]
    assert [f["flightId"] for f in _apply_flight_type_filter(flights, "s")] == ["SK3"]


def test_sensor_entity_applies_flight_type_per_entry():
    flights = [
        {"flightId": "SK1", "dom_int": "D"},
        {"flightId": "SK2", "dom_int": "I"},
        {"flightId": "SK3", "dom_int": "S"},
    ]
    coordinator = SimpleNamespace(data={"lastUpdate": "2025-01-01T12:00:00Z", "flights": flights})

    domestic_sensor = object.__new__(AvinorFlightsSensor)
    domestic_sensor.coordinator = coordinator
    domestic_sensor._entry = SimpleNamespace(
        data={
            "airport": "OSL",
            "direction": "A",
            "flight_type": "D",
            "time_from": 1,
            "time_to": 7,
        },
        options={},
    )

    all_types_sensor = object.__new__(AvinorFlightsSensor)
    all_types_sensor.coordinator = coordinator
    all_types_sensor._entry = SimpleNamespace(
        data={
            "airport": "TRF",
            "direction": "A",
            "flight_type": "",
            "time_from": 1,
            "time_to": 7,
        },
        options={},
    )

    assert domestic_sensor.native_value == 1
    assert [f["flightId"] for f in domestic_sensor.extra_state_attributes["flights"]] == ["SK1"]

    assert all_types_sensor.native_value == 3
    assert [f["flightId"] for f in all_types_sensor.extra_state_attributes["flights"]] == ["SK1", "SK2", "SK3"]


def test_compact_flight_contains_expected_keys():
    flight = {
        "flightId": "DY123",
        "airline": "DY",
        "schedule_time": "2025-01-01T13:00:00Z",
        "arr_dep": "D",
        "airport": "BGO",
        "status_code": "BRD",
        "gate": "A12",
        "check_in": "1",
        "dom_int": "D",
        "uniqueId": "u1",
        "status_time": "2025-01-01T12:30:00Z",
    }

    compact = _compact_flight(flight)
    assert compact == {
        "flightId": "DY123",
        "airline": "DY",
        "schedule_time": "2025-01-01T13:00:00Z",
        "arr_dep": "D",
        "airport": "BGO",
        "status_code": "BRD",
        "gate": "A12",
        "check_in": "1",
        "dom_int": "D",
    }


@pytest.mark.asyncio
async def test_airlabs_get_flight_details_requires_identifier():
    client = StubAirlabsClient({"response": {}})
    with pytest.raises(ValueError):
        await client.async_get_flight_details(api_key="k")


@pytest.mark.asyncio
async def test_airlabs_get_flight_details_returns_response_object():
    payload = {
        "request": {"key": {"api_key": "***"}},
        "response": {
            "flight_iata": "DY123",
            "status": "active",
            "dep_iata": "OSL",
        },
    }
    client = StubAirlabsClient(payload)
    details = await client.async_get_flight_details(api_key="k", flight_iata="DY123")
    assert details["flight_iata"] == "DY123"
    assert client.last_params["flight_iata"] == "DY123"
    assert client.last_params["api_key"] == "k"


@pytest.mark.asyncio
async def test_airlabs_get_flight_details_raises_on_error_payload():
    client = StubAirlabsClient({"error": "some_error", "message": "Bad request"})
    with pytest.raises(RuntimeError):
        await client.async_get_flight_details(api_key="k", flight_iata="DY123")


@pytest.mark.asyncio
async def test_airlabs_get_schedules_dedupes_and_classifies_routes():
    now = datetime.now(timezone.utc)

    def utc_in(hours: int) -> str:
        return (now + timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M")

    schedules_payload = {
        "response": [
            {
                "flight_iata": "KL8476",
                "cs_flight_iata": "SK1398",
                "airline_iata": "KL",
                "dep_iata": "CPH",
                "arr_iata": "TRF",
                "arr_time_utc": utc_in(1),
                "status": "landed",
            },
            {
                "flight_iata": "SK1398",
                "airline_iata": "SK",
                "dep_iata": "CPH",
                "arr_iata": "TRF",
                "arr_time_utc": utc_in(1),
                "status": "landed",
            },
            {
                "flight_iata": "WF481",
                "airline_iata": "WF",
                "dep_iata": "TRD",
                "arr_iata": "TRF",
                "arr_time_utc": utc_in(2),
                "status": "scheduled",
            },
            {
                "flight_iata": "FR6216",
                "airline_iata": "FR",
                "dep_iata": "KRK",
                "arr_iata": "TRF",
                "arr_time_utc": utc_in(3),
                "status": "scheduled",
            },
            {
                "flight_iata": "U28635",
                "airline_iata": "U2",
                "dep_iata": "LTN",
                "arr_iata": "TRF",
                "arr_time_utc": utc_in(4),
                "status": "active",
            },
            {
                "flight_iata": "TOO_OLD",
                "airline_iata": "XX",
                "dep_iata": "BGO",
                "arr_iata": "TRF",
                "arr_time_utc": utc_in(-20),
                "status": "landed",
            },
        ]
    }
    airport_payloads = {
        "CPH": {"response": [{"iata_code": "CPH", "country_code": "DK", "name": "Copenhagen Airport"}]},
        "TRD": {"response": [{"iata_code": "TRD", "country_code": "NO", "name": "Trondheim Airport"}]},
        "KRK": {"response": [{"iata_code": "KRK", "country_code": "PL", "name": "Krakow Airport"}]},
        "LTN": {"response": [{"iata_code": "LTN", "country_code": "GB", "name": "London Luton Airport"}]},
    }

    def payload(url, params):
        if url.endswith("/schedules"):
            return schedules_payload
        if url.endswith("/airports"):
            return airport_payloads[params["iata_code"]]
        raise AssertionError(f"Unexpected URL: {url}")

    client = StubAirlabsClient(payload)
    result = await client.async_get_schedules(
        api_key="k",
        airport="TRF",
        direction="A",
        time_from=2,
        time_to=6,
    )

    assert len(result["flights"]) == 4
    assert [flight["flightId"] for flight in result["flights"]] == ["SK1398", "WF481", "FR6216", "U28635"]
    assert [flight["dom_int"] for flight in result["flights"]] == ["S", "D", "S", "I"]
    assert [flight["status_code"] for flight in result["flights"]] == ["A", "E", "E", "EXP"]
    assert [flight["airport"] for flight in result["flights"]] == [
        "Copenhagen Airport",
        "Trondheim Airport",
        "Krakow Airport",
        "London Luton Airport",
    ]


@pytest.mark.asyncio
async def test_airlabs_get_schedules_for_departures_uses_arrival_airport_for_type():
    now = datetime.now(timezone.utc)
    dep_time = (now + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")

    def payload(url, params):
        if url.endswith("/schedules"):
            return {
                "response": [
                    {
                        "flight_iata": "DY123",
                        "airline_iata": "DY",
                        "dep_iata": "TRF",
                        "arr_iata": "LGW",
                        "dep_time_utc": dep_time,
                        "status": "scheduled",
                    }
                ]
            }
        if url.endswith("/airports"):
            return {"response": [{"iata_code": "LGW", "country_code": "GB", "name": "London Gatwick Airport"}]}
        raise AssertionError(f"Unexpected URL: {url}")

    client = StubAirlabsClient(payload)
    result = await client.async_get_schedules(
        api_key="k",
        airport="TRF",
        direction="D",
        time_from=0,
        time_to=2,
    )

    assert len(result["flights"]) == 1
    assert result["flights"][0]["airport"] == "London Gatwick Airport"
    assert result["flights"][0]["dom_int"] == "I"
    assert result["flights"][0]["arr_dep"] == "D"
