"""The Parasite Pool integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_BITCOIN_ADDRESS
from .coordinator import ParasiteDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Parasite Pool from a config entry."""
    coordinator = ParasiteDataUpdateCoordinator(
        hass, entry.data[CONF_BITCOIN_ADDRESS]
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Parasite Pool config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

