"""Config flow for Parasite Pool."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_BITCOIN_ADDRESS, DOMAIN, NAME

# Bech32 (bc1) and legacy/mainnet P2SH/P2PKH address shapes. Checksum validation
# remains the pool's responsibility; this prevents accidental empty/invalid input.
BITCOIN_ADDRESS_RE = re.compile(r"^(?:bc1[ac-hj-np-z02-9]{11,87}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})$")


class ParasiteConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Parasite Pool."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle initial setup."""
        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input[CONF_BITCOIN_ADDRESS].strip().lower()
            if not BITCOIN_ADDRESS_RE.fullmatch(address):
                errors[CONF_BITCOIN_ADDRESS] = "invalid_address"
            else:
                await self.async_set_unique_id(address)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"{NAME} ({address[:8]}…{address[-4:]})",
                    data={CONF_BITCOIN_ADDRESS: address},
                )

        schema = vol.Schema(
            {vol.Required(CONF_BITCOIN_ADDRESS): str}
            if user_input is None
            else {vol.Required(CONF_BITCOIN_ADDRESS, default=user_input[CONF_BITCOIN_ADDRESS]): str}
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

