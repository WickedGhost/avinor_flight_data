# Avinor Flight Data

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-blue.svg)](https://hacs.xyz/)
[![Hassfest](https://github.com/WickedGhost/avinor_flight_data/actions/workflows/hassfest.yml/badge.svg)](https://github.com/WickedGhost/avinor_flight_data/actions/workflows/hassfest.yml)
[![HACS Validation](https://github.com/WickedGhost/avinor_flight_data/actions/workflows/hacs.yml/badge.svg)](https://github.com/WickedGhost/avinor_flight_data/actions/workflows/hacs.yml)
[![Version 1.0.8](https://img.shields.io/badge/Version-1.0.8-orange.svg)](custom_components/avinor_flight_data/manifest.json)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Custom Home Assistant integration that keeps your dashboards up to date with arrivals and departures from the official Avinor data feed.

**Data source:** Flydata fra Avinor – https://partner.avinor.no/tjenester/flydata/

## Table of Contents
- [Overview](#overview)
- [Repository Structure](#repository-structure)
- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Flight Details (Airlabs)](#flight-details-airlabs)
- [Companion Lovelace Card](#companion-lovelace-card)
- [Example Dashboard Card](#example-dashboard-card)
- [Troubleshooting](#troubleshooting)
- [Release Notes](#release-notes)
- [Attribution](#attribution)

## Overview

- Polls Avinor's API on a recommended three-minute cadence and exposes the results as Home Assistant sensors.
- Includes Norwegian and English translations so the integration fits natively into your UI.
- Ships with tests that validate API parsing, helping future contributors keep behaviour stable.

## Repository Structure

- `custom_components/avinor_flight_data/` – Home Assistant integration package.
- `docs/assets/example_afd.png` – Example Lovelace card screenshot used in documentation.
- `tests/` – Unit tests covering the API parsing logic.

## Features

**Integration**
- Select from 300+ airports using a searchable dropdown.
- Choose arrivals or departures per sensor instance and control the time window (default: -1/+7 hours).
- Automatic refresh every three minutes, aligned with Avinor guidance.

**Lovelace Card (separate repository)**
- Responsive table layout that hides irrelevant columns for arrivals.
- Converts UTC timestamps to local time for readability.
- Translates status codes and airport identifiers into human-friendly labels.

## Installation

1. In Home Assistant, open HACS → Integrations → ⋮ → Custom repositories.
2. Add `https://github.com/WickedGhost/avinor_flight_data` as type `Integration`.
3. Install **Avinor Flight Data** from HACS.
4. Restart Home Assistant.
5. Navigate to Settings → Devices & Services → Add Integration → search for "Avinor Flight Data".
6. Follow the configuration flow to pick an airport, direction, and time window.

## Configuration

| Option           | Description                                           | Default |
|------------------|-------------------------------------------------------|---------|
| Airport           | Any Avinor airport (searchable list).                 | none    |
| Direction         | `A` (arrivals) or `D` (departures).                   | `D`     |
| Time from         | Hours back from now to include in results.            | `1`     |
| Time to           | Hours forward from now to include in results.         | `7`     |
| Airlabs API key   | Optional API key used for flight details.             | none    |

Each configured sensor reports the flight count as its state and exposes detailed flight data through the `flights` attribute.

## Flight Details (Airlabs)

This integration can optionally fetch details for a specific flight from the Airlabs Flight API:
https://airlabs.co/docs/flight

### Add your Airlabs API key

1. In Home Assistant, go to Settings → Devices & Services.
2. Find **Avinor Flight Data**.
3. Open **Configure** / **Options**.
4. Enter your key in the **airlabs_api_key** field.
5. Submit/save.

The key is optional. If you don’t set it, you can still call the service by passing `api_key` in the service data.

### Service: `avinor_flight_data.get_flight_details`

You can call this service from Developer Tools → Services, or from an automation.

Minimal example (IATA flight id):

```yaml
service: avinor_flight_data.get_flight_details
data:
  flight_iata: DY123
```

Override the configured key (useful for testing):

```yaml
service: avinor_flight_data.get_flight_details
data:
  api_key: YOUR_AIRLABS_KEY
  flight_iata: DY123
```

Notes:
- Provide at least one of: `flight_iata`, `flight_icao`, or `flight_number`.
- On Home Assistant versions that support service responses, the service returns the Airlabs `response` object.

## Companion Lovelace Card

Repository: https://github.com/WickedGhost/avinor-flight-card

**Install via HACS (Frontend)**
- HACS → Frontend → ⋮ → Custom repositories → add the card repository as `Lovelace`.
- Install **Avinor Flight Card** and restart if prompted.
- Ensure the resource `/hacsfiles/avinor-flight-card/avinor-flight-card.js` is listed under Settings → Dashboards → Resources.
- Edit your dashboard and add the "Avinor Flight Card" from the picker.

**Manual YAML alternative**

```yaml
type: custom:avinor-flight-card
entity: sensor.avinor_osl_d
title: Oslo Departures
```

## Example Dashboard Card

![Example Lovelace card](docs/assets/example_afd.png)

```yaml
type: custom:avinor-flight-card
entity: sensor.avinor_OSL_A
title: Ankomster OSL
```

## Troubleshooting

- Card missing from the picker: clear browser cache or add the card resource manually.
- Integration not listed: verify HACS installed it and restart Home Assistant.
- Empty sensor state: check the entity in Developer Tools → States and confirm the selected window includes flights.
- Resource 404 errors: confirm the path `/hacsfiles/avinor-flight-card/avinor-flight-card.js` exists after installation.

## Release Notes

- **0.2.1**
  - Split the Lovelace card into its own repository.
  - Updated HACS/Hassfest workflows to meet current validation requirements.
  - Refreshed documentation for the new repository layout.
- **0.2.0**
  - Ensured Python 3.10 compatibility during integration setup.
  - Hardened API error handling for timeouts, HTTP failures, and connection issues.
  - Cached the airport list for 24 hours to limit external requests during setup.
  - Respected options overrides (time window) after reload.
  - Escaped HTML in the Lovelace card and added initial API parsing tests.

## Attribution

"Flydata fra Avinor" – https://www.avinor.no/
