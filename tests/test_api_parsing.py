import asyncio
import pytest

from custom_components.avinor_flight_data.api import AvinorApiClient
from custom_components.avinor_flight_data.api import AirlabsApiClient
from custom_components.avinor_flight_data.sensor import _apply_flight_type_filter, _compact_flight


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
        self._payload = payload
        self.last_url = None
        self.last_params = None

    async def _get_json(self, url: str, params=None):
        self.last_url = url
        self.last_params = params
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
