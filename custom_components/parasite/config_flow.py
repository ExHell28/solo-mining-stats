"""Config flow for Parasite Pool."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_BITCOIN_ADDRESS,
    CONF_CKPOOL_URL,
    CONF_PROVIDER,
    DEFAULT_CKPOOL_URL,
    DOMAIN,
    NAME,
    PROVIDER_CKPOOL,
    PROVIDER_NAMES,
    PROVIDER_PARASITE,
)

# Bech32 (bc1) and legacy/mainnet P2SH/P2PKH address shapes. Checksum validation
# remains the pool's responsibility; this prevents accidental empty/invalid input.
BITCOIN_ADDRESS_RE = re.compile(r"^(?:bc1[ac-hj-np-z02-9]{11,87}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})$")


class ParasiteConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Parasite Pool."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._provider: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle initial setup."""
        if user_input is not None:
            self._provider = user_input[CONF_PROVIDER]
            return await self.async_step_connection()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PROVIDER, default=PROVIDER_PARASITE): vol.In(
                        {
                            PROVIDER_PARASITE: PROVIDER_NAMES[PROVIDER_PARASITE],
                            PROVIDER_CKPOOL: PROVIDER_NAMES[PROVIDER_CKPOOL],
                        }
                    )
                }
            ),
        )

    async def async_step_connection(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Collect the address and CKPool URL when applicable."""
        errors: dict[str, str] = {}
        provider = self._provider or PROVIDER_PARASITE

        if user_input is not None:
            address = user_input[CONF_BITCOIN_ADDRESS].strip().lower()
            ckpool_url = user_input.get(CONF_CKPOOL_URL, "").strip().rstrip("/")
            if not BITCOIN_ADDRESS_RE.fullmatch(address):
                errors[CONF_BITCOIN_ADDRESS] = "invalid_address"
            elif provider == PROVIDER_CKPOOL and (
                not urlparse(ckpool_url).scheme or not urlparse(ckpool_url).netloc
            ):
                errors[CONF_CKPOOL_URL] = "invalid_url"
            else:
                unique_id = f"{provider}:{ckpool_url}:{address}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                data = {
                    CONF_PROVIDER: provider,
                    CONF_BITCOIN_ADDRESS: address,
                }
                if provider == PROVIDER_CKPOOL:
                    data[CONF_CKPOOL_URL] = ckpool_url
                return self.async_create_entry(
                    title=(
                        f"{NAME} · {PROVIDER_NAMES[provider]} "
                        f"({address[:8]}…{address[-4:]})"
                    ),
                    data=data,
                )

        schema: dict[Any, Any] = {vol.Required(CONF_BITCOIN_ADDRESS): str}
        if provider == PROVIDER_CKPOOL:
            schema[vol.Required(CONF_CKPOOL_URL, default=DEFAULT_CKPOOL_URL)] = str
        return self.async_show_form(
            step_id="connection", data_schema=vol.Schema(schema), errors=errors
        )
