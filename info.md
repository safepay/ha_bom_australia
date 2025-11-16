# BOM Australia

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)

This Home Assistant custom component uses the [Bureau of Meteorology (BOM)](http://www.bom.gov.au) as a source for weather information for locations within Australia.

## Features

### 1. Weather Entity
A comprehensive weather entity that combines both daily and hourly forecasts in a single view, including:
- Current conditions (temperature, humidity, wind)
- 7-day daily forecasts
- Hourly forecasts
- Additional attributes: UV index, sunrise/sunset, fire danger, feels like temperature, dew point, station information

### 2. Binary Sensors (Warnings)
Individual binary sensors for different warning types:
- Flood, Severe Thunderstorm, Severe Weather, Fire, Tropical Cyclone, Storm, Wind, Sheep Graziers, Heat, Tsunami, Marine warnings
- Each sensor includes on/off state, severity information, issue/expiry times, and detailed warning data

### 3. Sensors (Observations & Forecasts)
Regular sensors for:
- Current observations (temperature, humidity, wind speed, rainfall, etc.)
- Forecast data points (min/max temperature, UV index, rain chance, fire danger, etc.)
- Astronomical data (sunrise/sunset times)

## Installation

1. Add this repository to HACS as a custom repository (or install from HACS default if available)
2. Install via HACS
3. Restart Home Assistant
4. Go to Configuration -> Integrations
5. Click "+ Add Integration"
6. Search for "BOM Australia"
7. Enter your latitude and longitude
8. The integration will automatically find the nearest BOM weather station
9. Configure which entities you want to create

**Note:** This integration uses a different directory name (`ha_bom_australia`) and entity prefix (`bom_`) to avoid conflicts with the original Bureau of Meteorology integration.

## Configuration

The integration will display the nearest weather station and observation station being used during setup. You can then configure which entities you want to create:
- Weather entity (with daily and hourly forecasts)
- Observation sensors (current conditions)
- Forecast sensors (future conditions)
- Warning binary sensors (weather alerts)

## Support

For issues, feature requests, or questions, please visit the [GitHub repository](https://github.com/safepay/ha_bom_australia/issues).
