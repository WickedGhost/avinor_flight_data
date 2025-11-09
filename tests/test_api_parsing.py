import asyncio
import pytest

from custom_components.avinor_flight_data.api import AvinorApiClient


class StubClient(AvinorApiClient):
    def __init__(self, flights_payload, airports_payload):
        # don't call super; we won't use the aiohttp session in tests
        self._flights_payload = flights_payload
        self._airports_payload = airports_payload

    async def _get_xml(self, url: str, params=None):
        if "airportNames" in url:
            return self._airports_payload
        return self._flights_payload


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
