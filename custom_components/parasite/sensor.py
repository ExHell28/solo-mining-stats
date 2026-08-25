"""Sensors for Parasite Pool."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, CONF_BITCOIN_ADDRESS, DOMAIN, NAME
from .coordinator import ParasiteDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class ParasiteSensorDescription(SensorEntityDescription):
    """Description for a Parasite Pool sensor."""

    data_key: str


SENSORS: tuple[ParasiteSensorDescription, ...] = (
    ParasiteSensorDescription(key="personal_hashrate", name="Personal Hashrate", data_key="personal_hashrate_th", native_unit_of_measurement="TH/s", suggested_display_precision=2),
    ParasiteSensorDescription(key="personal_best_difficulty", name="Personal Best Difficulty", data_key="personal_best_difficulty", icon="mdi:pickaxe"),
    ParasiteSensorDescription(key="total_work", name="Total Work", data_key="total_work", icon="mdi:chart-timeline-variant"),
    ParasiteSensorDescription(key="worker_count", name="Workers", data_key="worker_count", icon="mdi:server-network"),
    ParasiteSensorDescription(key="uptime", name="Uptime", data_key="uptime_seconds", device_class=SensorDeviceClass.DURATION, native_unit_of_measurement=UnitOfTime.SECONDS),
    ParasiteSensorDescription(key="rank", name="Rank", data_key="rank", icon="mdi:podium"),
    ParasiteSensorDescription(key="pool_hashrate", name="Pool Hashrate", data_key="pool_hashrate_ph", native_unit_of_measurement="PH/s", suggested_display_precision=2),
    ParasiteSensorDescription(key="pool_best_difficulty", name="Pool Best Difficulty", data_key="pool_best_difficulty", icon="mdi:pickaxe"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Parasite Pool sensors."""
    coordinator: ParasiteDataUpdateCoordinator = entry.runtime_data
    async_add_entities(ParasiteSensor(coordinator, entry, description) for description in SENSORS)


class ParasiteSensor(CoordinatorEntity[ParasiteDataUpdateCoordinator], SensorEntity):
    """A sensor backed by the Parasite Pool coordinator."""

    entity_description: ParasiteSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ParasiteDataUpdateCoordinator,
        entry: ConfigEntry,
        description: ParasiteSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        address = entry.data[CONF_BITCOIN_ADDRESS]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, address)},
            name=f"{NAME} ({address[:8]}…{address[-4:]})",
            manufacturer="Parasite Pool",
            model="Public API",
            configuration_url=f"https://parasite.space/user/{address}",
        )

    @property
    def native_value(self) -> Any:
        """Return the normalized state from the API."""
        return self.coordinator.data.get(self.entity_description.data_key)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose human-readable API representations where useful."""
        attributes: dict[str, Any] = {"attribution": ATTRIBUTION}
        if self.entity_description.key == "personal_best_difficulty":
            attributes["raw_difficulty"] = self.coordinator.data.get(
                "personal_best_difficulty_raw"
            )
        elif self.entity_description.key == "total_work":
            attributes["raw_total_work"] = self.coordinator.data.get("total_work_raw")
        elif self.entity_description.key == "uptime":
            attributes["api_value"] = self.coordinator.data.get("raw_uptime")
        elif self.entity_description.key == "pool_best_difficulty":
            attributes["api_value"] = self.coordinator.data.get("raw_pool_best_difficulty")
            attributes["raw_difficulty"] = self.coordinator.data.get(
                "pool_best_difficulty_raw"
            )
        return attributes
