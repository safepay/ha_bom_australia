# Bureau of Meteorology API Documentation

This folder contains documentation for the Bureau of Meteorology's undocumented APIs. These APIs are used by the BOM mobile app and https://weather.bom.gov.au.

All APIs return JSON data. Location selection uses geohashes for precision targeting.

**Geohash Requirements:**
- **Observations:** Requires **exactly 6-character geohash** (returns 400 error if not 6 chars)
- **Hourly forecasts:** Requires **exactly 6-character geohash** (returns 400 error if not 6 chars)
- **Daily forecasts, warnings:** Accept both 6 or 7-character geohash
- **Location search (coordinates):** Returns 7-character geohash
- **Location search (postcode):** Returns 7-character geohash
- **Critical:** When using geohashes from location search, **truncate to 6 characters** before querying observations or hourly forecasts

## Location Search

### Search by Coordinates

Fetch the geohash for a given latitude/longitude.

**Endpoint:** `https://api.weather.bom.gov.au/v1/locations?search={latitude},{longitude}`

**Example:** `https://api.weather.bom.gov.au/v1/locations?search=-12.463763,130.844398`

**Response:**
```json
{
  "metadata": {
    "response_timestamp": "2022-10-07T00:04:27Z",
    "copyright": "..."
  },
  "data": [
    {
      "geohash": "qvv117j",
      "id": "Darwin City-qvv117j",
      "name": "Darwin City",
      "postcode": null,
      "state": "NT"
    }
  ]
}
```

### Search by Postcode

Search for all locations within a specific Australian postcode. Returns multiple locations if the postcode covers multiple towns.

**Endpoint:** `https://api.weather.bom.gov.au/v1/locations?search={postcode}`

**Example:** `https://api.weather.bom.gov.au/v1/locations?search=4417`

**Response:**
```json
{
  "metadata": {
    "response_timestamp": "2025-11-18T21:24:08Z",
    "copyright": "..."
  },
  "data": [
    {
      "geohash": "r74n52x",
      "id": "Noorindoo-r74n52x",
      "name": "Noorindoo",
      "postcode": "4417",
      "state": "QLD"
    },
    {
      "geohash": "r71yk13",
      "id": "Oberina-r71yk13",
      "name": "Oberina",
      "postcode": "4417",
      "state": "QLD"
    },
    {
      "geohash": "r74j2pv",
      "id": "Surat-r74j2pv",
      "name": "Surat",
      "postcode": "4417",
      "state": "QLD"
    }
  ]
}
```

**Important Notes:**
- **Geohash Length:** Postcode search returns **7-character geohashes**. However, observations and hourly forecast endpoints require **exactly 6 characters**. You must truncate the geohash to 6 chars (e.g., `r74n52x` → `r74n52`) when querying those endpoints.
- **Warning Zones:** Each location within a postcode has its own unique geohash, which may result in different weather data and warnings. This is particularly important for warnings, as a single postcode can span multiple warning zones. Always select the specific town/location rather than relying on postcode-level geocoding.

## Location Info

Returns detailed information for a given geohash.

**Endpoint:** `https://api.weather.bom.gov.au/v1/locations/{geohash}`

**Response:**
```json
{
  "metadata": { "response_timestamp": "2022-10-07T00:27:52Z", "copyright": "..." },
  "data": {
    "geohash": "qvv117n",
    "timezone": "Australia/Darwin",
    "latitude": -12.463302612304688,
    "longitude": 130.84510803222656,
    "marine_area_id": "NT_MW007",
    "tidal_point": "NT_TP001",
    "has_wave": true,
    "id": "Darwin City-qvv117n",
    "name": "Darwin City",
    "state": "NT"
  }
}
```

## Observations

Returns observations from the nearest monitoring station.

**Endpoint:** `https://api.weather.bom.gov.au/v1/locations/{geohash}/observations`

**Response (abbreviated):**
```json
{
  "metadata": {
    "response_timestamp": "2022-10-07T00:19:26Z",
    "issue_time": "2022-10-07T00:11:02Z",
    "observation_time": "2022-10-07T00:10:00Z"
  },
  "data": {
    "temp": 30.5,
    "temp_feels_like": 33.6,
    "wind": { "speed_kilometre": 11, "speed_knot": 6, "direction": "SW" },
    "gust": { "speed_kilometre": 13, "speed_knot": 7 },
    "max_temp": { "time": "2022-10-07T00:01:00Z", "value": 30.7 },
    "min_temp": { "time": "2022-10-06T20:57:00Z", "value": 25.5 },
    "rain_since_9am": 0,
    "humidity": 64,
    "station": {
      "bom_id": "014015",
      "name": "Darwin Airport",
      "distance": 6899
    }
  }
}
```

## Daily Forecasts

Returns daily forecasts for the given geohash.

**Endpoint:** `https://api.weather.bom.gov.au/v1/locations/{geohash}/forecasts/daily`

**Response (showing first day):**
```json
{
  "metadata": {
    "response_timestamp": "2022-10-07T00:26:34Z",
    "issue_time": "2022-10-07T00:18:30Z"
  },
  "data": [
    {
      "date": "2022-10-06T14:30:00Z",
      "temp_max": 34,
      "temp_min": 25,
      "extended_text": "Partly cloudy. Medium chance of showers...",
      "icon_descriptor": "storm",
      "short_text": "Shower or two. Possible storm.",
      "rain": {
        "amount": { "min": 1, "max": 4, "units": "mm" },
        "chance": 70
      },
      "uv": {
        "category": "extreme",
        "max_index": 12,
        "start_time": "2022-10-06T23:20:00Z",
        "end_time": "2022-10-07T06:50:00Z"
      },
      "astronomical": {
        "sunrise_time": "2022-10-06T20:57:40Z",
        "sunset_time": "2022-10-07T09:13:56Z"
      },
      "fire_danger": "High",
      "fire_danger_category": {
        "text": "High",
        "default_colour": "#fedd3a"
      },
      "now": {
        "is_night": false,
        "now_label": "Max",
        "later_label": "Overnight Min",
        "temp_now": 34,
        "temp_later": 25
      }
    }
  ]
}
```

**Key Fields:**
- `icon_descriptor`: Weather condition (e.g., "sunny", "cloudy", "storm", "rain", "clear")
- `now`: Only present for day 0 (today), contains current/later temperature labels and values
- `fire_danger_category`: Contains color coding for fire danger visualization

## Hourly Forecasts

Returns hourly forecasts for the given geohash (provided in 3-hourly intervals).

**Endpoint:** `https://api.weather.bom.gov.au/v1/locations/{geohash}/forecasts/hourly`

**Response (abbreviated):**
```json
{
  "metadata": {
    "response_timestamp": "2022-10-07T00:36:56Z",
    "issue_time": "2022-10-07T00:18:30Z"
  },
  "data": [
    {
      "time": "2022-10-07T01:00:00Z",
      "temp": 29,
      "temp_feels_like": 33,
      "rain": {
        "amount": { "min": 0, "max": 1, "units": "mm" },
        "chance": 60
      },
      "wind": {
        "speed_kilometre": 9,
        "gust_speed_kilometre": 15,
        "direction": "SW"
      },
      "icon_descriptor": "mostly_sunny",
      "is_night": true,
      "next_three_hourly_forecast_period": "tonight",
      "relative_humidity": 69,
      "uv": 0
    }
  ]
}
```

## Warnings

Returns active warnings for the given geohash.

**Endpoint:** `https://api.weather.bom.gov.au/v1/locations/{geohash}/warnings`

**Response:**
```json
{
  "metadata": {
    "response_timestamp": "2022-10-07T01:08:55Z",
    "copyright": "..."
  },
  "data": [
    {
      "id": "NSW_FL049_IDN36503",
      "area_id": "NSW_FL049",
      "type": "flood_watch",
      "title": "Flood Watch for Queanbeyan and Molonglo Rivers",
      "short_title": "Flood Watch",
      "state": "NSW",
      "warning_group_type": "major",
      "issue_time": "2022-10-07T00:18:46Z",
      "expiry_time": "2022-10-08T06:18:46Z",
      "phase": "renewal"
    },
    {
      "id": "NSW_PW017_IDN29000",
      "area_id": "NSW_PW017",
      "type": "sheep_graziers_warning",
      "title": "Sheep Graziers Warning for Australian Capital Territory",
      "short_title": "Sheep Graziers Warning",
      "state": "NSW",
      "warning_group_type": "minor",
      "issue_time": "2022-10-07T00:21:57Z",
      "expiry_time": "2022-10-07T08:21:57Z",
      "phase": "renewal"
    }
  ]
}
```

**Key Fields:**
- `area_id`: Geographic zone identifier (format: `STATE_TYPE###` where TYPE is warning category like MW=Marine, PW=Public Weather, FL=Flood)
- `type`: Warning type (see Warning Types table below)
- `short_title`: Human-readable warning name (may differ from type)

### Warning Detail

Get detailed information for a specific warning.

**Endpoint:** `https://api.weather.bom.gov.au/v1/warnings/{id}`

**Response:**
```json
{
  "metadata": {
    "issue_time": "2022-10-09T00:00:41Z",
    "response_timestamp": "2022-10-09T00:03:12Z"
  },
  "data": {
    "id": "NSW_RC072_IDN36627",
    "type": "flood_warning",
    "title": "Flood Warning for Molonglo River",
    "short_title": "Flood Warning",
    "state": "NSW",
    "message": "<div class=\"product\">...</div>",
    "issue_time": "2022-10-09T00:00:41Z",
    "expiry_time": "2022-10-12T00:00:41Z",
    "phase": "renewal"
  }
}
```

### Warning Types

The following table shows all known BOM warning types and their support status in this integration:

| Warning Type | Status | Display Name |
|--------------|--------|--------------|
| `bushwalkers_alert` | ✅ Supported | Bushwalkers Alert |
| `fire_weather_warning` | ✅ Supported | Fire Weather Warning |
| `flood_watch` | ✅ Supported | Flood Watch |
| `flood_warning` | ✅ Supported | Flood Warning |
| `frost_warning` | ✅ Supported | Frost Warning |
| `hazardous_surf_warning` | ✅ Supported | Hazardous Surf Warning |
| `heatwave_warning` | ✅ Supported | Heatwave Warning |
| `marine_wind_warning` | ✅ Supported | Marine Wind Warning |
| `severe_thunderstorm_warning` | ✅ Supported | Severe Thunderstorm Warning |
| `severe_weather_warning` | ✅ Supported | Severe Weather Warning |
| `sheep_graziers_warning` | ✅ Supported | Sheep Graziers Warning |
| `tropical_cyclone_warning` | ✅ Supported | Tropical Cyclone Warning |
| `squall_warning` | ❌ Not Supported | Squall Warning |
| `road_weather_alert` | ❌ Not Supported | Road Weather Alert |
| `coastal_hazard_warning` | ❌ Not Supported | Coastal Hazard Warning |
| `ocean_wind_warning` | ❌ Not Supported | Ocean Wind Warning |
| `tsunami_alert` | ❌ Not Supported | Tsunami Alert |

**Notes:**
- Unsupported warning types will still appear in the main warnings sensor but will not have dedicated binary sensors.
- The BOM website documentation lists some warning types (e.g., `bushwalkers_weather_alert`) that differ from what the API actually returns (e.g., `bushwalkers_alert`).
- **Tropical Cyclone Warnings:** The BOM website lists multiple cyclone warning types (`tropical_cyclone_advice`, `tropical_cyclone_forecast_track_map`, `tropical_cyclone_ocean_wind_warning`, `tropical_cyclone_technical_bulletin`), but the API actually returns `tropical_cyclone_warning` for active cyclones. The website types have not been observed in production and may be legacy/theoretical.
- This table reflects actual API response values observed in production, not BOM's official documentation.

### Warning Field Values

**warning_group_type:**
- `major`
- `minor`

**phase:**
- `new`
- `update`
- `renewal`
- `downgrade`
- `upgrade`
- `final`
- `cancelled`

**message:**
Contains HTML content with outermost block `<div class="product">`.

## Copyright Notice

All API responses include a copyright notice:

> "This Application Programming Interface (API) is owned by the Bureau of Meteorology (Bureau). You must not use, copy or share it. Please contact us for more information on ways in which you can access our data. Follow this link http://www.bom.gov.au/inside/contacts.shtml to view our contact details."

This integration is for personal use only and not endorsed by the Bureau of Meteorology.
