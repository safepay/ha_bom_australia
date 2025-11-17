"""The BOM integration."""
import logging
from datetime import timedelta

from aiohttp.client_exceptions import ClientConnectorError
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import debounce
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    COLLECTOR,
    CONF_ENTITY_PREFIX,
    CONF_FORECASTS_CREATE,
    CONF_FORECASTS_DAYS,
    CONF_FORECASTS_MONITORED,
    CONF_OBSERVATIONS_CREATE,
    CONF_OBSERVATIONS_MONITORED,
    CONF_WARNINGS_CREATE,
    CONF_WARNINGS_MONITORED,
    CONF_WEATHER_NAME,
    COORDINATOR,
    DOMAIN,
    UPDATE_LISTENER,
)
from .PyBoM.collector import Collector

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["binary_sensor", "sensor", "weather"]

DEFAULT_SCAN_INTERVAL = timedelta(minutes=5)
DEBOUNCE_TIME = 60  # in seconds


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the BOM component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    if config_entry.version == 1:
        # Migrate from v1 to v2
        # Old v1 used forecasts_basename, new v2 uses weather_name
        new = {**config_entry.data}
        if "forecasts_basename" in new:
            new[CONF_WEATHER_NAME] = config_entry.data["forecasts_basename"]

        config_entry.version = 2
        hass.config_entries.async_update_entry(config_entry, data=new)

    _LOGGER.info("Migration to version %s successful", config_entry.version)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BOM from a config entry."""
    collector = Collector(entry.data[CONF_LATITUDE], entry.data[CONF_LONGITUDE])

    try:
        await collector.async_update()
    except ClientConnectorError as ex:
        raise ConfigEntryNotReady from ex

    coordinator = BomDataUpdateCoordinator(hass=hass, collector=collector)
    await coordinator.async_refresh()

    hass_data = hass.data.setdefault(DOMAIN, {})
    hass_data[entry.entry_id] = {
        COLLECTOR: collector,
        COORDINATOR: coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    update_listener = entry.add_update_listener(async_update_options)
    hass.data[DOMAIN][entry.entry_id][UPDATE_LISTENER] = update_listener

    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry):
    """Handle config entry updates."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Remove unconfigured entities and unload the config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    entity_registry = er.async_get(hass)
    entities = er.async_entries_for_config_entry(entity_registry, entry.entry_id)
    entities_to_keep = []

    # Get entity prefix (shared across all entities)
    location_name = entry.options.get(
        CONF_WEATHER_NAME, entry.data.get(CONF_WEATHER_NAME, "Home")
    )
    entity_prefix = entry.options.get(
        CONF_ENTITY_PREFIX,
        entry.data.get(
            CONF_ENTITY_PREFIX,
            f"bom_{location_name.lower().replace(' ', '_').replace('-', '_')}"
        )
    )

    # Keep the weather entity
    entities_to_keep.append(f"weather.{entity_prefix}")

    # if observations are enabled, keep the configured observation sensors
    if entry.options.get(CONF_OBSERVATIONS_CREATE) is True:
        for observation in entry.options.get(CONF_OBSERVATIONS_MONITORED, []):
            entities_to_keep.append(
                f"sensor.{entity_prefix}_{str(observation).lower()}"
            )

    # if forecasts are enabled, keep the configured forecast sensors
    if entry.options.get(CONF_FORECASTS_CREATE) is True:
        forecast_days = entry.options.get(CONF_FORECASTS_DAYS, entry.data.get(CONF_FORECASTS_DAYS, []))
        # Handle legacy integer format
        if isinstance(forecast_days, int):
            forecast_days = list(range(0, forecast_days + 1))
        elif not isinstance(forecast_days, list):
            forecast_days = []

        for day in forecast_days:
            for forecast in entry.options.get(CONF_FORECASTS_MONITORED, []):
                if forecast in [
                    "now_now_label",
                    "now_temp_now",
                    "now_later_label",
                    "now_temp_later",
                ]:
                    if day == 0:
                        entities_to_keep.append(
                            f"sensor.{entity_prefix}_{str(forecast).lower()}"
                        )
                else:
                    entities_to_keep.append(
                        f"sensor.{entity_prefix}_{str(day)}_{str(forecast).lower()}"
                    )

    # if warnings are enabled, keep the warning binary sensors
    if entry.options.get(CONF_WARNINGS_CREATE) is True:
        warnings_monitored = entry.options.get(
            CONF_WARNINGS_MONITORED,
            entry.data.get(CONF_WARNINGS_MONITORED, [])
        )
        for warning_type in warnings_monitored:
            entities_to_keep.append(f"binary_sensor.{entity_prefix}_warning_{warning_type}")

    _LOGGER.debug("Keeping %s", entities_to_keep)

    # remove any sensors that are not configured
    for entity in entities:
        if entity.entity_id not in entities_to_keep:
            entity_registry.async_remove(entity_id=entity.entity_id)
            _LOGGER.debug("Removing %s from entity registry", entity.entity_id)

    if unload_ok:
        update_listener = hass.data[DOMAIN][entry.entry_id][UPDATE_LISTENER]
        update_listener()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class BomDataUpdateCoordinator(DataUpdateCoordinator):
    """Data update coordinator for Bureau of Meteorology."""

    def __init__(self, hass: HomeAssistant, collector: Collector) -> None:
        """Initialise the data update coordinator."""
        self.collector = collector
        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_method=self.collector.async_update,
            update_interval=DEFAULT_SCAN_INTERVAL,
            request_refresh_debouncer=debounce.Debouncer(
                hass, _LOGGER, cooldown=DEBOUNCE_TIME, immediate=True
            ),
        )

        self.entity_registry_updated_unsub = self.hass.bus.async_listen(
            er.EVENT_ENTITY_REGISTRY_UPDATED, self.entity_registry_updated
        )

    @callback
    def entity_registry_updated(self, event):
        """Handle entity registry update events."""
        if event.data["action"] == "remove":
            self.remove_empty_devices()

    def remove_empty_devices(self):
        """Remove devices with no entities."""
        entity_registry = er.async_get(self.hass)
        device_registry = dr.async_get(self.hass)
        device_list = dr.async_entries_for_config_entry(
            device_registry, self.config_entry.entry_id
        )

        for device_entry in device_list:
            entities = er.async_entries_for_device(
                entity_registry, device_entry.id, include_disabled_entities=True
            )

            if not entities:
                _LOGGER.debug("Removing orphaned device: %s", device_entry.name)
                device_registry.async_update_device(
                    device_entry.id, remove_config_entry_id=self.config_entry.entry_id
                )
