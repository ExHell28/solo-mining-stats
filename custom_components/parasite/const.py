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
PROVIDER_CKPOOL_EU = "ckpool_eu"
CKPOOL_URLS = {
    PROVIDER_CKPOOL: "https://solo.ckpool.org",
    PROVIDER_CKPOOL_EU: "https://eusolo.ckpool.org",
}

PROVIDER_NAMES = {
    PROVIDER_PARASITE: "Parasite Pool",
    PROVIDER_CKPOOL: "CKPool",
    PROVIDER_CKPOOL_EU: "CKPool (EU)",
}

ATTRIBUTION = "Data provided by Parasite Pool"
