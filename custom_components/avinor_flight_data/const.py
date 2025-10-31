DOMAIN = "avinor_flight_data"

CONF_AIRPORT = "airport"
CONF_DIRECTION = "direction"
CONF_TIME_FROM = "time_from"
CONF_TIME_TO = "time_to"

DEFAULT_TIME_FROM = 1
DEFAULT_TIME_TO = 7

PLATFORMS = ["sensor"]

API_BASE = "https://asrv.avinor.no"
API_FLIGHTS = "/XmlFeed/v1.0"
API_AIRPORTS = "/airportNames/v1.0"

# Update every 3 minutes as suggested by Avinor docs
UPDATE_INTERVAL_SECONDS = 180
