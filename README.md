# Bureau of Meteorology Custom Component

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![GitHub Release][releases-shield]][releases]
[![License][license-shield]](LICENSE.md)
![Maintenance](https://img.shields.io/maintenance/yes/2025?style=for-the-badge)

### **This integration only supports locations within Australia.**

This Home Assistant custom component uses the [Bureau of Meteorology (BOM)](http://www.bom.gov.au) as a source for weather information.

## Installation

**Note:** This is NOT a HACS default integration. You must add it as a custom repository.

### Method 1: HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Click on the three dots in the top right corner
3. Select "Custom repositories"
4. Add the repository URL: `https://github.com/safepay/ha_bom_australia`
5. Select category: `Integration`
6. Click "Add"
7. Click "Install" on the BOM Australia card
8. Restart Home Assistant

### Method 2: Manual Installation

1. Download the latest release from [GitHub releases](https://github.com/safepay/ha_bom_australia/releases)
2. Copy the `custom_components/ha_bom_australia` directory to your Home Assistant's `custom_components` directory
3. Restart Home Assistant

**Note:** This integration uses a different directory name (`ha_bom_australia`) and entity prefix (`bom_`) to avoid conflicts with the original Bureau of Meteorology integration.

## Features

This integration provides three types of entities to organize your weather data:

### 1. Weather Entity
A comprehensive weather entity that combines both daily and hourly forecasts in a single view, including:
- Current conditions (temperature, humidity, wind speed, wind gust, wind bearing)
- Apparent temperature (feels like)
- Pressure (hPa)
- Visibility (km)
- Cloud coverage (oktas)
- Dew point
- UV index
- 7-day daily forecasts
- Hourly forecasts
- Additional attributes: sunrise/sunset, fire danger, station information, warning count

### 2. Binary Sensors (Warnings)
Individual binary sensors for different warning types:
- Flood warnings
- Severe thunderstorm warnings
- Severe weather warnings
- Fire weather warnings
- Tropical cyclone warnings
- Storm warnings
- Wind warnings
- Sheep graziers warnings
- Heat warnings
- Tsunami warnings
- Marine warnings

Each binary sensor includes:
- On/off state based on active warnings
- Severity information in attributes
- Issue and expiry times
- Detailed warning information

### 3. Sensors (Observations & Forecasts)
Regular sensors for:
- Current observations (temperature, humidity, wind speed, rainfall, etc.)
- Forecast data points (min/max temperature, UV index, rain chance, fire danger, etc.)
- Astronomical data (sunrise/sunset times)

## Breaking Changes

**Important:** If upgrading from an earlier version, please note:

1. **Warning Sensors**: Warning sensors have been completely redesigned:
   - **Old**: Single `sensor.bom_warnings` with list of warnings in attributes
   - **New**: Individual binary sensors for each warning type (e.g., `binary_sensor.{prefix}_warning_flood`)
   - Old warning sensors will need to be removed manually from your configuration

2. **Forecast Sensors**: Configuration has changed:
   - **Old**: Multi-select dropdown for forecast days
   - **New**: Single numeric input (0-7 days)
   - Existing forecast sensors will be recreated with the new configuration

3. **Device Organization**: Entities are now organized into separate devices:
   - `BOM {location}` - Weather entity
   - `BOM {location} Sensors` - Observation sensors
   - `BOM {location} Forecast Sensors` - Forecast sensors
   - `BOM {location} Warnings` - Warning binary sensors

**Note on Entity Naming**: The entity prefix is fully configurable during setup (defaults to `bom_{location}` but you can set it to match your existing setup). If you configure the same prefix as your previous installation, most entities will maintain their existing IDs.

**Recommendation**: For cleanest upgrade, remove the old integration completely before installing the new version, then reconfigure from scratch.

## Configuration

After you have installed the custom component (see above):

1. Goto the `Configuration` -> `Integrations` page.
2. On the bottom right of the page, click on the `+ Add Integration` sign to add an integration.
3. Search for `BOM Australia`. (If you don't see it, try refreshing your browser page to reload the cache.)
4. Enter your latitude and longitude (the integration will automatically find the nearest BOM weather station)
5. The integration will display the nearest weather station and observation station being used
6. Configure which entities you want to create (weather, observations, forecasts, warnings)
7. Click `Submit` to add the integration.

## Troubleshooting

Please set your logging for the custom_component to debug:

```yaml
logger:
  default: warn
  logs:
    custom_components.ha_bom_australia: debug
```

### Notes

1. This integration will not refresh data faster than once every 5 minutes.
2. All feature requests, issues and questions are welcome.

## About This Integration

This is a refactored version of the original [Bureau of Meteorology integration](https://github.com/bremor/bureau_of_meteorology), reorganized to avoid conflicts with existing integrations.

**Major improvements from the original:**
- Comprehensive weather entity with all standard Home Assistant properties (apparent temperature, pressure, visibility, cloud coverage, dew point, wind gust, UV index)
- Individual binary sensors for each warning type with phase-based filtering
- Streamlined config flow with visible checkboxes and human-readable labels
- Simplified entity naming with single prefix for all entities
- Can be installed alongside the original Bureau of Meteorology integration

## Credits


- Original integration by [@bremor](https://github.com/bremor) and [@makin-things](https://github.com/makin-things)

[hacs]: https://hacs.xyz
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/safepay/ha_bom_australia.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/safepay/ha_bom_australia.svg?style=for-the-badge
[releases]: https://github.com/safepay/ha_bom_australia/releases
