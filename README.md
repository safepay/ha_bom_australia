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

**Key differences from the original:**
- Uses directory name `ha_bom_australia` instead of `bureau_of_meteorology`
- All entities prefixed with "BOM" and unique IDs prefixed with "bom_"
- Consolidated weather entity with both daily and hourly forecasts
- Binary sensor platform for individual warning types
- Can be installed alongside the original Bureau of Meteorology integration

## Release Notes

### 1.2.2 - Weather Entity Enhancements

**Improvements:**
- Added comprehensive weather entity properties:
  - `native_apparent_temperature` - Feels like temperature
  - `native_wind_gust_speed` - Wind gust speed
  - `native_pressure` - Atmospheric pressure (hPa)
  - `native_visibility` - Visibility (km)
  - `cloud_coverage` - Cloud coverage in oktas
  - `native_dew_point` - Dew point temperature
  - `uv_index` - UV index from daily forecast
- All standard weather attributes now properly exposed for Home Assistant UI
- Cleaned up redundant attributes from extra_state_attributes

### 1.2.1 - Config Flow Polish

**Improvements:**
- Added human-readable labels for all sensors, warnings, and forecasts in config flow
- Reordered configuration steps: observations → warnings → forecasts (last)
- All checkboxes now default to checked/selected
- Improved descriptions for all configuration steps
- Updated both initial setup and reconfiguration (options) flows for consistency

### 1.2.0 - Major Config Flow Improvements

**Improvements:**
- Simplified entity prefix configuration (applies to ALL entities, not just weather)
- Fixed entity naming to prevent double prefix (e.g., bom_bom_melbourne)
- Changed all sensor selections from dropdowns to visible checkboxes
- Forecast days changed to single numeric input (0-7) with default of 5
- Improved wording throughout config flow
- Location name now auto-retrieved from BOM API

### 1.1.0 - Warning Sensor Improvements

**Improvements:**
- Enhanced warning binary sensors with individual attributes (ID, title, warning_group_type, phase, issue_time, expiry_time)
- Added phase-based filtering (warnings with cancelled/expired phases won't trigger sensors)
- Removed list-based attributes for cleaner UI
- Added HACS version support

### 1.0.0 - Initial Release (Refactored Fork)

**New Features:**
- **Comprehensive Weather Entity**: Single weather entity combining both daily and hourly forecasts with extensive attributes including UV index, sunrise/sunset, fire danger, feels like temperature, dew point, and station information
- **Binary Sensor Warnings Platform**: Individual binary sensors for each warning type (flood, severe thunderstorm, severe weather, fire, tropical cyclone, storm, wind, sheep graziers, heat, tsunami, marine) with on/off states, severity information, and detailed warning data
- **Improved Station Discovery**: Automatic detection of nearest BOM weather station based on coordinates with enhanced station information display during configuration
- **Organized Entity Types**: Clear separation into three categories:
  1. Weather entity (comprehensive forecasts)
  2. Binary sensors (warnings)
  3. Sensors (observations and forecast data points)

**Technical Details:**
- Domain: `ha_bom_australia`
- Entity prefix: `bom_`
- Compatible with Home Assistant 2023.9.0+
- Data refresh: Every 5 minutes (minimum)
- Supports both daily (7-day) and hourly forecasts

**Credits:**
- Original integration by [@bremor](https://github.com/bremor) and [@makin-things](https://github.com/makin-things)

[hacs]: https://hacs.xyz
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/safepay/ha_bom_australia.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/safepay/ha_bom_australia.svg?style=for-the-badge
[releases]: https://github.com/safepay/ha_bom_australia/releases
