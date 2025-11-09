# avinor_flight_data
Henter flydata fra Avinor og eksponerer dem som sensorer i Home Assistant.
# Avinor Flight Data (Home Assistant HACS)

Custom integration and Lovelace card to show Avinor flight data in Home Assistant.

Data source: Flydata fra Avinor – https://partner.avinor.no/tjenester/flydata/

This repository contains:
- A Home Assistant custom integration (`custom_components/avinor_flight_data`) that fetches flights for a selected airport and direction, within a time window.
- A simple Lovelace card (`www/community/avinor-flight-card/avinor-flight-card.js`) that renders a table with one row per flight and the requested columns.

## Features

- Configure per entry:
	- Airport (IATA) – searchable dropdown
	- Direction – A (Arrivals) or D (Departures)
	- TimeFrom (hours back, default 1)
	- TimeTo (hours forward, default 7)
- Updates every 3 minutes (per Avinor guidance)
- Sensor state = number of flights; attributes include flights list and metadata
- Lovelace card shows a table with columns: flightId, dom_int, schedule_time, airport, check_in, gate, status code

## Installation (HACS)

1) In HACS, add this repository as a custom repository (type: Integration).
2) Install "Avinor Flight Data".
3) Restart Home Assistant.

Optionally, for the Lovelace card:
1) In HACS, also add the repo as a custom repository (type: Frontend) or place the JS file manually under `www/community/avinor-flight-card/`.
2) Add a Lovelace resource pointing to `/hacsfiles/avinor-flight-card/avinor-flight-card.js` (HACS managed) or `/local/community/avinor-flight-card/avinor-flight-card.js` (manual).

## Configuration

Add the integration via Settings → Devices & Services → Add Integration → "Avinor Flight Data".

Select:
- Airport (IATA)
- Direction (A=Arrivals, D=Departures)
- Time from (hours back)
- Time to (hours forward)

The integration creates one sensor per configuration, named like `sensor.avinor_OSL_A` with:

- state: number of flights
- attributes:
	- airport, direction, time_from, time_to, last_update
	- flights: array of flight objects with keys: flightId, dom_int, schedule_time, airport, check_in, gate, status_code

## Lovelace Card Usage

Example card configuration:

```yaml
type: 'custom:avinor-flight-card'
entity: sensor.avinor_OSL_A
title: Ankomster OSL
```

The card reads the flights from the sensor's attributes and renders a table with the required columns.

## Notes

- Times from the API are UTC (ISO 8601). The card displays them as-is.
- Avinor recommends polling every 3 minutes and caching on your side; this integration follows that guidance.
- If the airport list cannot be fetched during setup, a small built-in fallback list (OSL, BGO, TRD, SVG) is used.

## Changes

- 0.2.0
	- Fix Python 3.10 compatibility in integration setup.
	- More robust API error handling (timeouts, HTTP and connection errors logged clearly).
	- Cache airport list for 24h during config/options flow to reduce API calls.
	- Sensor attributes now respect options overrides (time window) after reload.
	- Lovelace card: escape HTML to prevent injection from unexpected data.
	- Initial unit tests for API parsing.

## Attribution

"Flydata fra Avinor" – https://www.avinor.no/
