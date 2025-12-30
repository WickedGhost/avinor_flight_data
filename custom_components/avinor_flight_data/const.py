DOMAIN = "avinor_flight_data"

CONF_AIRPORT = "airport"
CONF_DIRECTION = "direction"
CONF_TIME_FROM = "time_from"
CONF_TIME_TO = "time_to"

# Optional Airlabs integration (flight details)
CONF_AIRLABS_API_KEY = "airlabs_api_key"

# Client-side filtering options
CONF_FLIGHT_TYPE = "flight_type"  # Avinor dom_int field

DEFAULT_TIME_FROM = 1
DEFAULT_TIME_TO = 7

DEFAULT_FLIGHT_TYPE = ""  # empty = all

PLATFORMS = ["sensor"]

# Services
SERVICE_GET_FLIGHT_DETAILS = "get_flight_details"

API_BASE = "https://asrv.avinor.no"
API_FLIGHTS = "/XmlFeed/v1.0"
API_AIRPORTS = "/airportNames/v1.0"

AIRLABS_API_BASE = "https://airlabs.co/api/v9"
AIRLABS_API_FLIGHT_DETAILS = "/flight"

# Update every 3 minutes as suggested by Avinor docs
UPDATE_INTERVAL_SECONDS = 180
