# Avinor Flight Data (Home Assistant Integration)

Custom integration to fetch and expose Avinor flight data in Home Assistant. A separate Lovelace card is available to visualize the data in a table (see below).

**Data source:** Flydata fra Avinor – https://partner.avinor.no/tjenester/flydata/

## 📦 What's Included

This repository provides:
- **🔧 Integration** (`custom_components/avinor_flight_data`) – Fetches flight data as Home Assistant sensors

For the UI:
- **🎨 Lovelace Card (separate repo)** – https://github.com/WickedGhost/avinor-flight-card

## ✨ Features

### Integration Features
- **🛫 Airport Selection** - 300+ airports via searchable dropdown
- **📍 Direction Choice** - Arrivals (A) or Departures (D)
- **⏰ Time Window** - Configurable hours back/forward (default: 1h back, 7h forward)
- **🔄 Auto Updates** - Every 3 minutes (per Avinor guidance)
- **🌐 Multi-language** - Norwegian and English support

### Card Features
- **🎯 Smart Layout** - Hides Check-in/Gate columns for arrivals
- **🌍 Timezone Support** - Shows local time (not UTC)
- **🏷️ Readable Labels** - Airport names instead of codes (OSL → Oslo)
- **📊 Status Descriptions** - Human-readable status (D → Departed)
- **🔍 Visual Editor** - Easy configuration through UI
- **📱 responsive Design** - Works on all devices

## 🚀 Installation (HACS)

### 1) Install the Integration
1. HACS → Integrations → ⋮ Menu → Custom Repositories
2. Add repository: `https://github.com/WickedGhost/avinor_flight_data` (Category: Integration)
3. Install "Avinor Flight Data"
4. Restart Home Assistant
5. Go to Settings → Devices & Services → Add Integration → "Avinor Flight Data"
6. Configure: airport, direction, time window

## 🎨 Lovelace Card (separate repository)

To visualize the flights in a table, install the companion card from its own repository:

Repository: https://github.com/WickedGhost/avinor-flight-card

### Install via HACS (Frontend)
1. HACS → Frontend → ⋮ Menu → Custom Repositories
2. Add repository: `https://github.com/WickedGhost/avinor-flight-card` (Category: Lovelace)
3. Install "Avinor Flight Card"
4. If needed, add resource: Settings → Dashboards → Resources →
	- URL: `/hacsfiles/avinor-flight-card/avinor-flight-card.js`
	- Resource type: JavaScript Module
5. Edit dashboard → Add Card → Search "Avinor Flight Card"

### Manual YAML (alternative)
```yaml
type: custom:avinor-flight-card
entity: sensor.avinor_osl_d    # Required: Your flight sensor
title: "Oslo Departures"       # Optional: Custom title
```

### 🔧 Troubleshooting
- **Card not in picker**: Hard refresh browser (Ctrl+Shift+R), ensure resource added, or use manual YAML
- **Integration not found**: Check Settings → Devices & Services for "Avinor Flight Data"
- **No data showing**: Verify sensor exists in Developer Tools → States
-- **Resource 404**: Verify resource path `/hacsfiles/avinor-flight-card/avinor-flight-card.js` is present

## ⚙️ Integration Configuration

The integration is included with the HACS installation. Configure it as follows:

### Configuration Options:
- **🛫 Airport**: Select from 300+ airports (searchable dropdown)
- **📍 Direction**: A (Arrivals) or D (Departures)  
- **⏰ Time From**: Hours back from now (default: 1)
- **⏰ Time To**: Hours forward from now (default: 7)

### Sensor Output
Creates sensor like `sensor.avinor_osl_d` with:
- **State**: Number of flights found
- **Attributes**:
  - `airport`, `direction`, `time_from`, `time_to`, `last_update`
  - `flights`: Array of flight objects with all flight details

## 📊 Card Display Features

The Lovelace card automatically adapts based on flight direction:

### Departures (D) - Shows All Columns:
| Flight | Type | Scheduled | Airport | Check-in | Gate | Status |
|--------|------|-----------|---------|----------|------|--------|
| SK123 | International | 14:30 | Copenhagen | 12:30 | A15 | Boarding |

### Arrivals (A) - Hides Irrelevant Columns:
| Flight | Type | Scheduled | Airport | Status |
|--------|------|-----------|---------|--------|
| SK456 | Schengen | 15:45 | Stockholm | Landed |

### Smart Features:
- **🌍 Timezone Aware**: Shows local time (not UTC)
- **🏷️ Human Readable**: "Oslo" instead of "OSL", "Departed" instead of "D"
- **📱 Responsive**: Adapts to screen size
- **✨ Visual Editor**: Configure through Home Assistant UI

Example card configuration:

```yaml
type: 'custom:avinor-flight-card'
entity: sensor.avinor_OSL_A
title: Ankomster OSL
```

## 🖼️ Example

![Example Avinor Flight Card output](example_afd.png)

The card reads the flights from the sensor's attributes and renders a table with the required columns.

## Notes

- Times from the API are UTC (ISO 8601). The card converts and displays local time.
- Avinor recommends polling every 3 minutes and caching on your side; this integration follows that guidance.
- If the airport list cannot be fetched during setup, a small built-in fallback list (OSL, BGO, TRD, SVG) is used.

## Changes

- 0.2.1
	- Restructure: integration-only repo; Lovelace card moved to separate repository.
	- Updated HACS/Hassfest workflows to pass validation.
	- Updated documentation for installing the card via HACS Frontend from its repo.

- 0.2.0
	- Fix Python 3.10 compatibility in integration setup.
	- More robust API error handling (timeouts, HTTP and connection errors logged clearly).
	- Cache airport list for 24h during config/options flow to reduce API calls.
	- Sensor attributes now respect options overrides (time window) after reload.
	- Lovelace card: escape HTML to prevent injection from unexpected data.
	- Initial unit tests for API parsing.

## Attribution

"Flydata fra Avinor" – https://www.avinor.no/
