"""Constants for the Parasite Pool integration."""

from datetime import timedelta

DOMAIN = "parasite"
NAME = "Solo Mining Stats"
API_BASE_URL = "https://parasite.space/api"
UPDATE_INTERVAL = timedelta(seconds=30)
REQUEST_TIMEOUT = 15

CONF_BITCOIN_ADDRESS = "bitcoin_address"
CONF_PROVIDER = "provider"
CONF_CKPOOL_URL = "ckpool_url"

PROVIDER_PARASITE = "parasite"
PROVIDER_CKPOOL = "ckpool"
DEFAULT_CKPOOL_URL = "https://solo.ckpool.org"

PROVIDER_NAMES = {
    PROVIDER_PARASITE: "Parasite Pool",
    PROVIDER_CKPOOL: "CKPool",
}

ATTRIBUTION = "Data provided by Parasite Pool"
