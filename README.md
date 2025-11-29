# Home Assistant BoM Custom Component

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release][releases-shield]][releases]
[![License][license-shield]](LICENSE.md)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2023.9.0+-blue.svg)](https://www.home-assistant.io/)
![Maintenance](https://img.shields.io/maintenance/yes/2025)

### **This integration only supports locations within Australia.**

This Home Assistant custom component uses the [Bureau of Meteorology (BOM)](http://www.bom.gov.au) as a source for weather information.

The BoM API is not meant to be accessed via 3rd parties.
For a fully supported, albeit not free API, use my [WillyWeather](https://github.com/safepay/willyweather-forecast-home-assistant) integration.

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

**Note:** This integration uses a different directory name (`ha_bom_australia`) and entity prefix (`BoM_`) to avoid conflicts with the original Bureau of Meteorology integration.

## Features

This integration provides three types of entities to organize your weather data:

### 1. Weather Entity
A comprehensive weather entity that combines both daily and hourly forecasts in a single view, including:
- Current conditions (temperature, humidity, wind speed, wind gust, wind bearing)
- Apparent temperature (feels like)
- Dew point (calculated)
- UV index
- 7-day daily forecasts
- Hourly forecasts
- Additional attributes: sunrise/sunset, fire danger, station information, warning count

### 2. Binary Sensors (Warnings)
Individual binary sensors for different warning types (matching BOM API):
- Flood Watch
- Flood Warning
- Sheep Graziers Warning
- Severe Thunderstorm Warning
- Severe Weather Warning
- Marine Wind Warning
- Hazardous Surf Warning
- Heatwave Warning
- Frost Warning
- Bushwalkers Alert
- Fire Weather Warning
- Tropical Cyclone Warning

Each binary sensor includes:
- On/off state based on active warnings (excludes only cancelled warnings)
- Warning phase information (new, update, renewal, downgrade, upgrade, final, cancelled)
- Severity and warning group type in attributes
- Issue and expiry times
- Detailed warning information

### 3. Sensors (Observations & Forecasts)
Regular sensors for:
- Current observations (temperature, humidity, wind speed, rainfall, etc.)
- Calculated observation sensors (dew point, delta-T)
- Forecast data points (min/max temperature, UV index, rain chance, fire danger, etc.)
- Astronomical data (sunrise/sunset times)
- Handles the "null" value for today's minimum forecast temperature that the API produces late each day

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

**Note on Entity Naming**: The entity prefix is fully configurable during setup (defaults to `BoM_{location}` but you can set it to match your existing setup). If you configure the same prefix as your previous installation, most entities will maintain their existing IDs.

**Recommendation**: For cleanest upgrade, remove the old integration completely before installing the new version, then reconfigure from scratch.

## Configuration

After you have installed the custom component (see above):

1. Goto the `Configuration` -> `Integrations` page.
2. On the bottom right of the page, click on the `+ Add Integration` sign to add an integration.
3. Search for `BOM Australia`. (If you don't see it, try refreshing your browser page to reload the cache.)
4. Enter your location:
   - **Default**: Latitude and longitude fields are pre-populated with your Home Assistant's location - just click through to use your current location
   - **Alternative**: Check "Use Australian postcode instead?" and enter a postcode (e.g., 3000 for Melbourne) to set up sensors for a different location
   - If multiple locations are found for the postcode, select your specific town from the dropdown
5. The integration will display the nearest weather location and observation station being used
   - **Note**: Some remote locations only have forecast and warning data available (no observation station)
6. Configure which entities you want to create (weather, observations, forecasts, warnings)
7. Click `Submit` to add the integration.

### Postcode Support

The integration supports Australian postcode lookup for easier configuration. This is especially useful when:
- Setting up sensors for multiple locations (e.g., Melbourne and Sydney)
- You don't know the exact coordinates but know the postcode
- You want to quickly add a location without looking up coordinates

When you enter a postcode, the integration queries the BOM API to find all locations within that postcode. If multiple towns are found (common in rural areas), you'll be presented with a dropdown to select your specific town or locality. This ensures you get the correct weather data and warnings for your exact location, as warning zones can vary within a single postcode.

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
- Comprehensive weather entity with standard Home Assistant properties (temperature, humidity, wind speed/gust/bearing, apparent temperature, dew point, UV index)
- Calculated observation sensors (dew point using Magnus-Tetens formula, delta-T for fire weather)
- Individual binary sensors for each warning type using actual BOM API warning types with accurate phase-based filtering (only excludes cancelled warnings)
- Australian postcode lookup for easier multi-location setup
- Streamlined config flow with visible checkboxes and human-readable labels
- Simplified entity naming with single prefix for all entities
- Material Design Icon integration for consistent UI appearance
- Can be installed alongside the original Bureau of Meteorology integration

## Credits


- Original integration by [@bremor](https://github.com/bremor) and [@makin-things](https://github.com/makin-things)

[hacs]: https://hacs.xyz
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg
[license-shield]: https://img.shields.io/github/license/safepay/ha_bom_australia.svg
[releases-shield]: https://img.shields.io/github/release/safepay/ha_bom_australia.svg
[releases]: https://github.com/safepay/ha_bom_australia/releases
