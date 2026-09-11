"""Platform for sensor integration."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import (
    ATTR_DATE,
    ATTR_STATE,
    EntityCategory,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util
from homeassistant.util import slugify
from zoneinfo import ZoneInfo

from . import BomDataUpdateCoordinator
from .const import (
    ATTRIBUTION,
    COLLECTOR,
    CONF_ENTITY_PREFIX,
    CONF_FORECASTS_CREATE,
    CONF_FORECASTS_DAYS,
    CONF_FORECASTS_MONITORED,
    CONF_OBSERVATIONS_CREATE,
    CONF_OBSERVATIONS_MONITORED,
    CONF_WEATHER_NAME,
    COORDINATOR,
    DOMAIN,
    SHORT_ATTRIBUTION,
    MODEL_NAME,
    OBSERVATION_SENSOR_TYPES,
    FORECAST_SENSOR_TYPES,
    ATTR_API_CONDITION,
    ATTR_API_EXTENDED_TEXT,
    ATTR_API_FIRE_DANGER,
    ATTR_API_HOURS_UNTIL_RAIN,
    ATTR_API_NEXT_RAIN_AMOUNT,
    DAY_INDEPENDENT_FORECAST_SENSORS,
    LAST_UPDATED_SENSOR,
    RAIN_EXPECTED_THRESHOLD_PERCENT,
    WARNINGS_SENSOR,
    entity_unique_id,
    forecast_unique_id,
)
from .PyBoM.collector import Collector
from .PyBoM.helpers import RainChunk, parse_iso_datetime, rain_chunks, rain_event

_LOGGER = logging.getLogger(__name__)

MAX_STATE_LENGTH: Final[int] = 251  # Maximum length for sensor state before truncation


def format_short_time(value: datetime) -> str:
    """Format a time as e.g. '6:12am'.

    Avoids strftime's "%-I" hour padding modifier, which is a glibc extension
    and raises ValueError on Windows, and its locale-dependent "%p".
    """
    meridiem = "am" if value.hour < 12 else "pm"
    return f"{value.hour % 12 or 12}:{value.minute:02d}{meridiem}"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in HA."""
    hass_data = hass.data[DOMAIN][config_entry.entry_id]

    new_entities = []
    create_observations = config_entry.options.get(
        CONF_OBSERVATIONS_CREATE, config_entry.data.get(CONF_OBSERVATIONS_CREATE)
    )
    create_forecasts = config_entry.options.get(
        CONF_FORECASTS_CREATE, config_entry.data.get(CONF_FORECASTS_CREATE)
    )

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

    if create_observations is True:
        observations = config_entry.options.get(
            CONF_OBSERVATIONS_MONITORED,
            config_entry.data.get(CONF_OBSERVATIONS_MONITORED, None),
        )

        # The rain sensors are chosen alongside the observations but read the
        # hourly forecast, so they have classes of their own.
        rain_sensors = {
            ATTR_API_HOURS_UNTIL_RAIN: HoursUntilRainSensor,
            ATTR_API_NEXT_RAIN_AMOUNT: NextRainAmountSensor,
        }
        descriptions = {description.key: description for description in OBSERVATION_SENSOR_TYPES}
        for observation in observations or []:
            description = descriptions.get(observation)
            if description is None:
                # Still in the stored selection, but no longer a sensor type.
                continue
            sensor_class = rain_sensors.get(observation, ObservationSensor)
            new_entities.append(
                sensor_class(
                    hass_data,
                    location_name,
                    entity_prefix,
                    observation,
                    description,
                )
            )

    if create_forecasts is True:
        forecast_days = config_entry.options.get(
            CONF_FORECASTS_DAYS, config_entry.data.get(CONF_FORECASTS_DAYS, [])
        )
        forecasts_monitored = config_entry.options.get(
            CONF_FORECASTS_MONITORED, config_entry.data.get(CONF_FORECASTS_MONITORED)
        )

        # Ensure forecast_days is a list
        if isinstance(forecast_days, int):
            # Legacy support: convert old integer format to list
            forecast_days = list(range(0, forecast_days + 1))
        elif not isinstance(forecast_days, list):
            forecast_days = []

        descriptions = {description.key: description for description in FORECAST_SENSOR_TYPES}
        for day in forecast_days:
            for forecast in forecasts_monitored or []:
                description = descriptions.get(forecast)
                if description is None:
                    # Still in the stored selection, but no longer a sensor type.
                    continue
                if forecast in DAY_INDEPENDENT_FORECAST_SENSORS:
                    # Describe the whole forecast rather than one day of it, so
                    # they are created once, and their entity id carries no day
                    # number. async_unload_entry reads the same list when it
                    # prunes the registry, so the two agree on the id.
                    if day == 0:
                        new_entities.append(
                            NowLaterSensor(
                                hass_data,
                                location_name,
                                entity_prefix,
                                forecast,
                                description,
                            )
                        )
                else:
                    # Limit extended_text and fire_danger to 4 days (0-3) as API data is not available beyond that
                    if forecast in [ATTR_API_EXTENDED_TEXT, ATTR_API_FIRE_DANGER] and day >= 4:
                        continue
                    new_entities.append(
                        ForecastSensor(
                            hass_data,
                            location_name,
                            entity_prefix,
                            day,
                            forecast,
                            description,
                        )
                    )

    # Always create the data-freshness sensor: it reports on whatever was
    # fetched, so it is useful regardless of which sensors were selected.
    new_entities.append(
        LastUpdatedSensor(
            hass_data,
            location_name,
            entity_prefix,
        )
    )

    # Always create catch-all warnings sensor (shows all warnings, even unknown types)
    new_entities.append(
        WarningsSensor(
            hass_data,
            location_name,
            entity_prefix,
        )
    )

    # Note: Individual warning binary sensors are handled by binary_sensor platform
    # See binary_sensor.py for warning binary sensor implementation

    if new_entities:
        async_add_entities(new_entities, update_before_add=False)


class SensorBase(CoordinatorEntity[BomDataUpdateCoordinator], SensorEntity):
    """Base representation of a BOM Sensor."""

    _attr_attribution = ATTRIBUTION

    def __init__(self, hass_data, location_name, entity_prefix, sensor_name, description: SensorEntityDescription, device_type: str = "Sensors") -> None:
        """Initialize the sensor."""
        super().__init__(hass_data[COORDINATOR])
        self.collector: Collector = hass_data[COLLECTOR]
        self.location_name: str = location_name
        self.entity_prefix: str = entity_prefix
        self.sensor_name: str = sensor_name
        self.entity_description = description

        # Determine device identifier suffix based on device type
        device_suffix = device_type.lower().replace(" ", "_")

        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, f"{self.entity_prefix}_{device_suffix}")},
            manufacturer=SHORT_ATTRIBUTION,
            model=f"{MODEL_NAME} - {device_type}",
            name=f"BOM {self.location_name} {device_type}",
        )

        # Home Assistant would otherwise build a new entity's id from the device
        # name followed by the entity name. Ask for the id these have always
        # had, which keeps the bom_ prefix the weather cards rely on even though
        # the friendly name no longer shows it. It applies only when an entity
        # is first created: anything already in the registry keeps its own id.
        self.entity_id = f"sensor.{slugify(f'BOM {self.name}')}"

    def _timezone(self) -> ZoneInfo | None:
        """Return the BOM location's timezone, or None when it is unavailable."""
        location = (self.collector.locations_data or {}).get("data") or {}
        timezone = location.get("timezone")
        return ZoneInfo(timezone) if timezone else None


class ObservationSensor(SensorBase):
    """Representation of a BOM Observation Sensor."""

    def __init__(self, hass_data, location_name, entity_prefix, sensor_name, description: SensorEntityDescription,):
        """Initialize the sensor."""
        super().__init__(hass_data, location_name, entity_prefix, sensor_name, description, device_type="Sensors")

    @property
    def unique_id(self) -> str:
        """Return Unique ID string."""
        return entity_unique_id(self.entity_prefix, self.sensor_name)

    def _observations(self) -> dict[str, Any]:
        """Return the observations payload, or an empty dict when unavailable."""
        data = (self.collector.observations_data or {}).get("data")
        return data if isinstance(data, dict) else {}

    def _today_forecast(self) -> dict[str, Any]:
        """Return today's daily forecast, or an empty dict when unavailable."""
        data = (self.collector.daily_forecasts_data or {}).get("data")
        if not data:
            return {}
        return data[0] if isinstance(data[0], dict) else {}

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the sensor."""
        attr: dict[str, Any] = {}

        tzinfo = self._timezone()
        if tzinfo is None:
            return attr

        # BOM can send "metadata": null, which is not iterable.
        metadata = (self.collector.observations_data or {}).get("metadata")
        if metadata is None:
            return attr

        for key, value in metadata.items():
            try:
                attr[key] = parse_iso_datetime(value).astimezone(tzinfo).isoformat()
            except ValueError:
                attr[key] = value

        attr.update(self._observations().get("station") or {})

        # Add extended forecast text for condition sensor
        if self.sensor_name == ATTR_API_CONDITION:
            extended_text = self._today_forecast().get("extended_text")
            if extended_text:
                attr["forecast_text"] = extended_text

        # Only proceed for max_temp or min_temp
        if self.sensor_name not in ("max_temp", "min_temp"):
            return attr

        # These arrive as {"value": ..., "time": ...} rather than a bare number.
        sensor_data = self._observations().get(self.sensor_name)
        if not isinstance(sensor_data, dict):
            return attr

        time_str = sensor_data.get("time")
        if not time_str:
            return attr

        # We have all required data, now add the time_observed attribute
        attr["time_observed"] = parse_iso_datetime(time_str).astimezone(tzinfo).isoformat()
        return attr

    @property
    def native_value(self) -> Any:
        """Return the value reported by the sensor."""
        # The condition sensor has no observation of its own: it reports the
        # daily forecast's short_text.
        if self.sensor_name == ATTR_API_CONDITION:
            short_text = self._today_forecast().get("short_text")
            if not short_text:
                return None
            # Remove trailing punctuation for cleaner display
            return short_text.rstrip(".!,;:")

        value = self._observations().get(self.sensor_name)
        if value is None:
            return None
        if self.sensor_name in ("max_temp", "min_temp"):
            # These arrive as {"value": ..., "time": ...} rather than a bare number.
            return value.get("value") if isinstance(value, dict) else None
        return value

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"{self.location_name} {self.sensor_name.replace('_', ' ').title()}"


class ForecastSensor(SensorBase):
    """Representation of a BOM Forecast Sensor."""

    def __init__(self, hass_data, location_name, entity_prefix, day, sensor_name, description: SensorEntityDescription,):
        """Initialize the sensor."""
        self.day = day
        super().__init__(hass_data, location_name, entity_prefix, sensor_name, description, device_type="Forecast Sensors")

    @property
    def unique_id(self) -> str:
        """Return Unique ID string."""
        return forecast_unique_id(self.entity_prefix, self.day, self.sensor_name)

    def _day_forecast(self) -> dict[str, Any] | None:
        """Return this sensor's day of the daily forecast, or None when absent."""
        data = (self.collector.daily_forecasts_data or {}).get("data")
        if not data or self.day >= len(data):
            return None
        return data[self.day] if isinstance(data[self.day], dict) else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the sensor."""
        attr: dict[str, Any] = {}

        # If there is no data for this day, do not add attributes for this day.
        day_data = self._day_forecast()
        if day_data is None:
            return attr
        tzinfo = self._timezone()
        if tzinfo is None:
            return attr

        # BOM can send "metadata": null, which is not iterable.
        metadata = (self.collector.daily_forecasts_data or {}).get("metadata") or {}
        for key, value in metadata.items():
            try:
                attr[key] = parse_iso_datetime(value).astimezone(tzinfo).isoformat()
            except ValueError:
                attr[key] = value

        date = day_data.get("date")
        try:
            attr[ATTR_DATE] = parse_iso_datetime(date).astimezone(tzinfo).isoformat()
        except ValueError:
            attr[ATTR_DATE] = date

        if self.sensor_name == "fire_danger" and day_data.get("fire_danger") is not None:
            # Safely get fire_danger_category (may be null after ~4pm, but restored by coordinator)
            fire_danger_category = day_data.get("fire_danger_category")
            if fire_danger_category and fire_danger_category.get("default_colour"):
                attr["color_fill"] = fire_danger_category["default_colour"]
                attr["color_text"] = "#ffffff" if (fire_danger_category.get("text") == "Catastrophic") else "#000000"
        if self.sensor_name.startswith("extended"):
            attr[ATTR_STATE] = day_data.get("extended_text")
        return attr

    def _uv_forecast(self, day_data: dict[str, Any]) -> str | None:
        """Build the UV protection summary string."""
        uv_category = day_data.get("uv_category")
        if uv_category is None:
            return None
        category = uv_category.replace("veryhigh", "very high").title()
        max_index = day_data.get("uv_max_index")
        no_protection_required = (
            f"Sun protection not required, UV Index predicted to reach "
            f"{max_index} [{category}]"
        )

        local = self._timezone()
        if local is None:
            return no_protection_required

        # BOM omits both UV times overnight and outside the UV season, and has
        # been seen returning one of the pair without the other.
        try:
            start_time = parse_iso_datetime(day_data.get("uv_start_time")).astimezone(local)
            end_time = parse_iso_datetime(day_data.get("uv_end_time")).astimezone(local)
        except ValueError:
            return no_protection_required

        return (
            f"Sun protection recommended from {format_short_time(start_time)} to "
            f"{format_short_time(end_time)}, UV Index predicted to reach "
            f"{max_index} [{category}]"
        )

    @property
    def native_value(self) -> Any:
        """Return the value reported by the sensor."""
        # If there is no data for this day, report no value for this day.
        day_data = self._day_forecast()
        if day_data is None:
            return None

        if self.device_class == SensorDeviceClass.TIMESTAMP:
            # A TIMESTAMP sensor must hand Home Assistant a timezone-aware
            # datetime, which it then renders as UTC. Anything else — a missing
            # value, or a string BOM has changed the format of — raises out of
            # SensorEntity.state, so it has to become None here instead.
            # parse_iso_datetime stamps UTC on an offset-less timestamp, which
            # keeps a naive datetime from ever reaching that check.
            try:
                return parse_iso_datetime(day_data.get(self.sensor_name))
            except ValueError:
                return None

        if self.sensor_name == "uv_forecast":
            return self._uv_forecast(day_data)

        value = day_data.get(self.sensor_name)

        if self.sensor_name == "uv_category" and value is not None:
            value = value.replace("veryhigh", "very high").title()
        # Strip trailing period from short_text for cleaner display
        elif self.sensor_name == "short_text" and isinstance(value, str):
            value = value.rstrip(".")

        if isinstance(value, str) and len(value) > MAX_STATE_LENGTH:
            value = value[:MAX_STATE_LENGTH] + "..."
        return value

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"{self.location_name} {self.sensor_name.replace('_', ' ').title()} {self.day}"


class NowLaterSensor(SensorBase):
    """Representation of a BOM Forecast Sensor."""

    def __init__(self, hass_data, location_name, entity_prefix, sensor_name, description: SensorEntityDescription,):
        """Initialize the sensor."""
        super().__init__(hass_data, location_name, entity_prefix, sensor_name, description, device_type="Forecast Sensors")

    @property
    def unique_id(self) -> str:
        """Return Unique ID string."""
        return entity_unique_id(self.entity_prefix, self.sensor_name)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the sensor."""
        if not self.collector.daily_forecasts_data or "metadata" not in self.collector.daily_forecasts_data:
            return {}
        return dict(self.collector.daily_forecasts_data["metadata"])

    @property
    def native_value(self) -> Any:
        """Return the value reported by the sensor."""
        data = (self.collector.daily_forecasts_data or {}).get("data")
        if not data:
            return None
        return data[0].get(self.sensor_name) if isinstance(data[0], dict) else None

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"{self.location_name} {self.sensor_name.replace('_', ' ').title()}"


class RainSensorBase(SensorBase):
    """Base for the sensors describing the next rain event in the hourly forecast.

    This is not a radar nowcast. BOM's hourly forecast repeats one rain chance
    and amount across each 3-hour block, so the block is the finest resolution
    there is. A block counts as wet at RAIN_EXPECTED_THRESHOLD_PERCENT or more
    with some rain amount forecast, so Next Rain Amount never reads 0 while rain
    is expected. The event is the first run of consecutive wet blocks, which may include
    the one under way. Both sensors read it through the same helpers, so they
    always describe the same event, and both move on to the next wet block as
    each one ends.
    """

    def __init__(self, hass_data, location_name, entity_prefix, sensor_name, description: SensorEntityDescription,):
        """Initialize the sensor."""
        super().__init__(hass_data, location_name, entity_prefix, sensor_name, description, device_type="Sensors")

    @property
    def unique_id(self) -> str:
        """Return Unique ID string."""
        return entity_unique_id(self.entity_prefix, self.sensor_name)

    def _outlook(self) -> tuple[datetime, list[RainChunk], list[RainChunk]]:
        """Return now, the blocks yet to end, and the next rain event among them."""
        now = dt_util.utcnow()
        chunks = rain_chunks((self.collector.hourly_forecasts_data or {}).get("data"), now)
        return now, chunks, rain_event(chunks, RAIN_EXPECTED_THRESHOLD_PERCENT)

    @staticmethod
    def _status(chunks: list[RainChunk], event: list[RainChunk]) -> str:
        """Say whether rain is expected, not expected, or cannot be told.

        No rain coming and no forecast to go on both leave the state without an
        event to describe; this says which, so the one is not mistaken for the
        other.
        """
        if event:
            return "expected"
        if any(chunk.chance is not None for chunk in chunks):
            return "none_expected"
        return "no_data"

    def _local(self, value: datetime) -> str:
        """Return a time as ISO 8601 in the BOM location's timezone."""
        tzinfo = self._timezone()
        return (value.astimezone(tzinfo) if tzinfo else value).isoformat()

    def _chunk_attributes(self, chunk: RainChunk) -> dict[str, Any]:
        """Return the attributes describing one block."""
        return {
            "chunk_start": self._local(chunk.start),
            "chunk_end": self._local(chunk.end),
            "chance": chunk.chance,
            "at_least": chunk.at_least,
            "up_to": chunk.up_to,
            "condition": chunk.condition,
        }

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"{self.location_name} {self.sensor_name.replace('_', ' ').title()}"


class HoursUntilRainSensor(RainSensorBase):
    """Hours until the next rain event.

    Counts to the start of the first wet block: the earliest the rain could
    arrive, not the minute it will. Reads 0 while the block under way is wet.
    """

    @property
    def native_value(self) -> float | None:
        """Return the hours until the first wet block starts."""
        now, _, event = self._outlook()
        if not event:
            # No rain in the forecast, or no forecast. Unknown rather than a
            # made-up number; the status attribute says which.
            return None
        return round(max((event[0].start - now).total_seconds(), 0) / 3600, 1)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the sensor."""
        now, chunks, event = self._outlook()
        attrs: dict[str, Any] = {
            "status": self._status(chunks, event),
            "threshold_percent": RAIN_EXPECTED_THRESHOLD_PERCENT,
            # The block under way, whether or not it reaches the threshold.
            "chance_now": chunks[0].chance if chunks and chunks[0].start <= now else None,
        }
        if event:
            attrs.update(self._chunk_attributes(event[0]))
        return attrs


class NextRainAmountSensor(RainSensorBase):
    """How much rain the current or next wet block could bring, in mm.

    The state is BOM's upper figure, the amount with a 25% chance of being
    exceeded: "up to". Its lower figure is 0 for most showers, which would read
    as no rain at all. The state follows the event block by block, so a light
    start and a heavier middle each show as they arrive; the attributes cover
    the whole event, for notice of what is still to come.
    """

    # The block-by-block breakdown is for dashboards and templates. Recording it
    # would store the whole list again with every state change.
    _unrecorded_attributes = frozenset({"chunks"})

    @property
    def native_value(self) -> float | None:
        """Return the upper rain amount of the current or next wet block."""
        _, chunks, event = self._outlook()
        if event:
            return event[0].up_to
        # No rain in the forecast is a true zero; no forecast is unknown.
        return 0 if self._status(chunks, event) == "none_expected" else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the sensor."""
        _, chunks, event = self._outlook()
        attrs: dict[str, Any] = {
            "status": self._status(chunks, event),
            "threshold_percent": RAIN_EXPECTED_THRESHOLD_PERCENT,
        }
        if not event:
            return attrs

        attrs.update(self._chunk_attributes(event[0]))
        # Sums of each block's upper figure: a "could reach" total for the
        # event, not a strict 25% figure for the sum.
        amounts = [chunk for chunk in event if chunk.up_to is not None]
        heaviest = max(amounts, key=lambda chunk: chunk.up_to, default=None)
        attrs.update(
            event_start=self._local(event[0].start),
            event_end=self._local(event[-1].end),
            event_total=round(sum(chunk.up_to for chunk in amounts), 1) if amounts else None,
            heaviest=heaviest.up_to if heaviest else None,
            heaviest_start=self._local(heaviest.start) if heaviest else None,
            heaviest_end=self._local(heaviest.end) if heaviest else None,
            chunks=[
                {
                    "start": self._local(chunk.start),
                    "end": self._local(chunk.end),
                    "chance": chunk.chance,
                    "at_least": chunk.at_least,
                    "up_to": chunk.up_to,
                    "condition": chunk.condition,
                }
                for chunk in event
            ],
        )
        return attrs


class LastUpdatedSensor(SensorBase):
    """When BOM data was last retrieved, and how old each piece of it is.

    The state is the newest ``response_timestamp`` across the datasets that were
    fetched, as a timestamp — Home Assistant renders a timestamp device class in
    RFC 3339. There is no single "last update" in the API: each endpoint carries
    its own times, and they diverge by well over an hour in normal operation
    (the hourly forecast is reissued far less often than the observations), so
    every one is exposed as an attribute rather than collapsed into the state.

    This also makes a degraded fetch visible. ``Collector`` falls back to a cache
    up to 24 hours old when BOM is unreachable, which keeps entities populated
    but silently stale; ``oldest_response`` is then much older than the state.
    """

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    # Off unless asked for. It answers "is the data stale", which most
    # installations never need to ask, and it would otherwise appear
    # unannounced on every existing install.
    _attr_entity_registry_enabled_default = False

    # Collector attribute per dataset, and the prefix its times appear under.
    _SOURCES = (
        ("observations", "observations_data"),
        ("daily", "daily_forecasts_data"),
        ("hourly", "hourly_forecasts_data"),
        ("warnings", "warnings_data"),
    )
    _TIME_KEYS = ("response_timestamp", "issue_time", "next_issue_time", "observation_time")

    def __init__(self, hass_data, location_name, entity_prefix):
        """Initialize the sensor."""
        description = SensorEntityDescription(
            key=LAST_UPDATED_SENSOR,
            name="Last Updated",
            device_class=SensorDeviceClass.TIMESTAMP,
            icon="mdi:clock-check-outline",
        )
        super().__init__(hass_data, location_name, entity_prefix, LAST_UPDATED_SENSOR, description)

    @property
    def unique_id(self) -> str:
        """Return Unique ID string."""
        return entity_unique_id(self.entity_prefix, self.sensor_name)

    def _times(self) -> dict[str, datetime]:
        """Return every timestamp BOM supplied, keyed ``<dataset>_<field>``."""
        found: dict[str, datetime] = {}
        for label, attribute in self._SOURCES:
            # BOM can send "metadata": null, and a dataset may not have been
            # fetched at all, so neither the data nor the metadata is assumed.
            metadata = (getattr(self.collector, attribute, None) or {}).get("metadata") or {}
            for key in self._TIME_KEYS:
                if key in metadata:
                    try:
                        found[f"{label}_{key}"] = parse_iso_datetime(metadata[key])
                    except ValueError:
                        continue
        return found

    @property
    def native_value(self) -> Any:
        """Return the most recent response timestamp across the datasets."""
        responses = [
            value for key, value in self._times().items()
            if key.endswith("_response_timestamp")
        ]
        return max(responses) if responses else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return every timestamp, plus the oldest response for staleness."""
        attrs: dict[str, Any] = dict(self._times())
        responses = [v for k, v in attrs.items() if k.endswith("_response_timestamp")]
        if responses:
            attrs["oldest_response"] = min(responses)
        return attrs

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"{self.location_name} Last Updated"


class WarningsSensor(SensorBase):
    """Representation of a BOM Warnings Sensor (catch-all for all warnings)."""

    def __init__(self, hass_data, location_name, entity_prefix):
        """Initialize the sensor."""
        # Create a basic description for the warnings sensor
        description = SensorEntityDescription(
            key=WARNINGS_SENSOR,
            name="Warnings",
            icon="mdi:alert-circle",
        )
        super().__init__(hass_data, location_name, entity_prefix, WARNINGS_SENSOR, description, device_type="Warnings")

    @property
    def unique_id(self) -> str:
        """Return Unique ID string."""
        return entity_unique_id(self.entity_prefix, self.sensor_name)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the sensor."""
        attr = {}

        # Add all warnings data to attributes
        if (
            self.collector.warnings_data
            and "data" in self.collector.warnings_data
        ):
            # Include the warnings array
            attr["warnings"] = self.collector.warnings_data["data"]

            # Include metadata
            if "metadata" in self.collector.warnings_data:
                attr["response_timestamp"] = self.collector.warnings_data["metadata"].get("response_timestamp")

        return attr

    @property
    def native_value(self) -> int:
        """Return the count of active warnings.

        Reports 0 rather than None when there is no warnings data, so the state
        stays numeric for template arithmetic and history graphs. A BOM outage
        is therefore indistinguishable from a quiet day.
        """
        if not self.collector.warnings_data:
            return 0
        # BOM can send "data": null, which len() cannot take.
        return len(self.collector.warnings_data.get("data") or [])

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"{self.location_name} Warnings"
