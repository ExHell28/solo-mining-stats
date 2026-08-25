"""Constants for the Parasite Pool integration."""

from datetime import timedelta

DOMAIN = "parasite"
NAME = "Parasite Pool"
API_BASE_URL = "https://parasite.space/api"
UPDATE_INTERVAL = timedelta(seconds=30)
REQUEST_TIMEOUT = 15

CONF_BITCOIN_ADDRESS = "bitcoin_address"

ATTRIBUTION = "Data provided by Parasite Pool"

