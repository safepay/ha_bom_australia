"""Platform for binary sensor integration (warnings)."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BomDataUpdateCoordinator
from .const import (
    ATTRIBUTION,
    COLLECTOR,
    CONF_ENTITY_PREFIX,
    CONF_WARNINGS_CREATE,
    CONF_WARNINGS_MONITORED,
    CONF_WEATHER_NAME,
    COORDINATOR,
    DOMAIN,
    SHORT_ATTRIBUTION,
    MODEL_NAME,
    WARNING_TYPES,
)
from .PyBoM.collector import Collector

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add binary sensors for warnings if enabled."""
    # Check if warnings are enabled
    if not config_entry.options.get(CONF_WARNINGS_CREATE, config_entry.data.get(CONF_WARNINGS_CREATE, False)):
        _LOGGER.debug("Warning binary sensors not enabled in config")
        return

    hass_data = hass.data[DOMAIN][config_entry.entry_id]

    # Get location name and entity prefix (shared across all sensors)
    location_name = config_entry.options.get(
        CONF_WEATHER_NAME, config_entry.data.get(CONF_WEATHER_NAME, "Home")
    )
    entity_prefix = config_entry.options.get(
        CONF_ENTITY_PREFIX,
        config_entry.data.get(
            CONF_ENTITY_PREFIX,
            f"bom_{location_name.lower().replace(' ', '_').replace('-', '_')}"
        )
    )

    # Get which warning types to create
    warnings_monitored = config_entry.options.get(
        CONF_WARNINGS_MONITORED,
        config_entry.data.get(CONF_WARNINGS_MONITORED, list(WARNING_TYPES.keys()))
    )

    # Create binary sensors for each enabled warning type
    new_entities = []
    for warning_type in warnings_monitored:
        if warning_type in WARNING_TYPES:
            warning_info = WARNING_TYPES[warning_type]
            new_entities.append(
                BomWarningSensor(hass_data, location_name, entity_prefix, warning_type, warning_info)
            )

    if new_entities:
        async_add_entities(new_entities, update_before_add=False)


class BomWarningSensor(BinarySensorEntity):
    """Representation of a BOM Warning Binary Sensor."""

    def __init__(
        self, hass_data, location_name: str, entity_prefix: str, warning_type: str, warning_info: dict
    ) -> None:
        """Initialize the binary sensor."""
        self.collector: Collector = hass_data[COLLECTOR]
        self.coordinator: BomDataUpdateCoordinator = hass_data[COORDINATOR]
        self.location_name = location_name
        self.entity_prefix = entity_prefix
        self.warning_type = warning_type
        self.warning_info = warning_info
        self._attr_device_class = BinarySensorDeviceClass.SAFETY
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, f"{self.entity_prefix}_binary_warning_sensors")},
            manufacturer=SHORT_ATTRIBUTION,
            model=MODEL_NAME,
            name=f"BOM {self.location_name} Binary Warning Sensors",
        )

    async def async_added_to_hass(self) -> None:
        """Set up a listener and load data."""
        self.async_on_remove(self.coordinator.async_add_listener(self._update_callback))
        self._update_callback()

    @callback
    def _update_callback(self) -> None:
        """Load data from integration."""
        self.async_write_ha_state()

    @property
    def should_poll(self) -> bool:
        """Entities do not individually poll."""
        return False

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"BOM {self.location_name} {self.warning_info['name']}"

    @property
    def unique_id(self) -> str:
        """Return unique ID string."""
        return f"{self.entity_prefix}_warning_{self.warning_type}"

    @property
    def icon(self) -> str:
        """Return the icon for the sensor."""
        return self.warning_info.get("icon", "mdi:alert")

    @property
    def is_on(self) -> bool:
        """Return true if there is an active warning of this type."""
        try:
            if (
                self.collector.warnings_data
                and "data" in self.collector.warnings_data
            ):
                warnings = self.collector.warnings_data["data"]
                # Check if any warning matches this type
                for warning in warnings:
                    warning_id = warning.get("id", "")
                    warning_title = warning.get("title", "").lower()
                    warning_type_api = warning.get("type", "").lower()

                    # Match based on type or title containing keywords
                    if self._matches_warning_type(warning_id, warning_title, warning_type_api):
                        return True
            return False
        except (KeyError, TypeError) as err:
            _LOGGER.debug(f"Error checking warning state for {self.warning_type}: {err}")
            return False

    def _matches_warning_type(self, warning_id: str, warning_title: str, warning_type_api: str) -> bool:
        """Check if a warning matches this sensor's type."""
        # Convert everything to lowercase for comparison
        warning_id = warning_id.lower()
        warning_title = warning_title.lower()
        warning_type_api = warning_type_api.lower()
        sensor_type = self.warning_type.lower()

        # Direct type match
        if sensor_type in warning_type_api:
            return True

        # Keyword matching based on warning type
        keywords_map = {
            "flood": ["flood"],
            "severe_thunderstorm": ["severe thunderstorm", "thunderstorm"],
            "severe_weather": ["severe weather"],
            "fire": ["fire weather", "fire danger", "total fire ban"],
            "tropical_cyclone": ["tropical cyclone", "cyclone"],
            "storm": ["storm"],
            "wind": ["wind", "strong wind", "damaging wind"],
            "sheep_graziers": ["sheep graziers", "sheep"],
            "heat": ["heatwave", "extreme heat", "heat"],
            "tsunami": ["tsunami"],
            "marine": ["marine", "coastal"],
        }

        keywords = keywords_map.get(sensor_type, [])
        for keyword in keywords:
            if keyword in warning_title or keyword in warning_id:
                return True

        return False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the sensor."""
        try:
            attrs = {}
            active_warnings = []

            if (
                self.collector.warnings_data
                and "data" in self.collector.warnings_data
            ):
                warnings = self.collector.warnings_data["data"]
                for warning in warnings:
                    warning_id = warning.get("id", "")
                    warning_title = warning.get("title", "").lower()
                    warning_type_api = warning.get("type", "").lower()

                    if self._matches_warning_type(warning_id, warning_title, warning_type_api):
                        warning_data = {
                            "title": warning.get("title"),
                            "type": warning.get("type"),
                            "issue_time": warning.get("issue_time"),
                            "expiry_time": warning.get("expiry_time"),
                            "id": warning.get("id"),
                            "short_title": warning.get("short_title"),
                            "state": warning.get("state"),
                            "warning_group_type": warning.get("warning_group_type"),
                        }
                        # Add severity if available (minor, moderate, severe)
                        if "phase" in warning:
                            warning_data["severity"] = warning.get("phase")

                        active_warnings.append(warning_data)

            attrs["warnings"] = active_warnings
            attrs["warning_count"] = len(active_warnings)
            attrs["attribution"] = ATTRIBUTION

            return attrs
        except (KeyError, TypeError) as err:
            _LOGGER.debug(f"Error building warning attributes for {self.warning_type}: {err}")
            return {"attribution": ATTRIBUTION, "warnings": [], "warning_count": 0}
