# Bureau of Meteorology — current website API

The API behind the redesigned bom.gov.au (the React front-end at `www.bom.gov.au`).
It supersedes the older `api.weather.bom.gov.au/v1` geohash API on the web, but
does not replace it outright: nothing on the new site calls that host any more,
while the BOM Weather mobile app still uses it exclusively (§11).

**Base URL**

```
https://api.bom.gov.au/apikey/v1
```

Scope of this document: **location search, forecasts, observations and warnings**.
The site also exposes `/products` (raw text bulletins) and a large `/mapping` tree
(ArcGIS + WMTS tiles for radar and forecast layers); those are out of scope here.

> Undocumented and unsupported. Everything below was derived by observing the
> traffic of www.bom.gov.au and probing the endpoints directly.
> Last verified **10 September 2026 (AEST)**.

---

## 1. Authentication, CORS and formats

| | |
|---|---|
| Auth | **None required today.** The path segment `apikey` is a red herring. |
| Key header | The front-end supports `X-API-Key`, populated from Drupal settings. In production every one of those settings (`location_api_key`, `forecast_api_key`, `observation_api_key`, `warnings_api_key`, …) is an **empty string**, and requests with no header at all return 200. |
| CORS | Permissive — browser calls from other origins succeed. |
| Server-side | Works from a plain `curl`/`requests` call; no `Origin` or `Referer` needed. **But set a User-Agent** — see the bot-manager row. |
| Bot manager | `api.bom.gov.au` sits behind Akamai. A request sent with the *default* `curl/8.x` User-Agent is answered `404` with an HTML "your access is blocked … does not support web scraping" page, not JSON. Any other User-Agent — a browser string, or an application's own token — returns 200 with no header, cookie or challenge. The older `api.weather.bom.gov.au` host has no such filter. |
| Format | JSON (`/products` is `text/plain`). |
| Times | **All timestamps are UTC**, ISO 8601 with `Z`. Local dates are derived from the `timezone` you pass or from the place's own timezone. |
| Rate limits | None observed. Be polite: the site itself polls observations at roughly 1-minute resolution and forecasts every few hours. |

Errors come back as JSON in one of two shapes:

```json
{"errors":[{"code":"DPD-E-005","detail":"Validation error with parameter: duration; Reason: Missing required query parameter; Value: (null)","id":"…","source":{"parameter":"duration"}}]}
{"type":"about:blank","title":"Bad Request","status":400,"detail":"Required parameter 'coordinate' is not present.","instance":"/v1/locations/places/search"}
```

An unrouted path returns `404 { "errors": [{ "code": "404", "detail": "No Mapping Rule matched" }] }`.
The error bodies are genuinely useful — they name the missing parameter and, for
enums, the accepted values.

---

## 2. Identifiers

This is the main conceptual change from the old API. There is no geohash. Four
different identifiers are used, and one endpoint (`places/details`) maps between them.

| Identifier | Example | Used by |
|---|---|---|
| `place_id` | `bnsw_pt131` (Sydney), `o117178255`, `a13562` | `places/details`, `forecasts/daily-list` |
| Forecast grid cell | `x=658`, `y=223` | `forecasts/daily`, `forecasts/1hourly`, `forecasts/3hourly` |
| `bom_stn_num` | `66214` (Sydney – Observatory Hill) | all `observations/*` |
| `aac` (BOM area code) | `NSW_PT131`, `NSW_FA001`, `NSW_TP007` | `forecasts/texts`, `forecasts/tidal`, `warnings/*` |

`place_id` prefixes seen: `b…` for BOM forecast towns/districts (`bnsw_`, `bvic_`,
`bqld_`, `bwa_`, `bsa_`, `btas_`, `bnt_`), `o…` and `a…` for gazetteer localities.

The normal bootstrap for an integration is: **autocomplete → place details → cache
the grid cell, station number and aacs**, then poll the data endpoints with those.

---

## 3. Location search

### 3.1 Autocomplete (the site's search box)

```
GET /locations/places/autocomplete
```

| Param | Req | Notes |
|---|---|---|
| `name` | yes | Free text: town, suburb, postcode |
| `limit` | no | Site uses `5` |
| `website-sort` | no | `true` — BOM's own relevance ordering |
| `include-states` | no | `true` — allow state entries in results |
| `include-districts` | no | `true` — allow forecast-district entries |

```bash
curl 'https://api.bom.gov.au/apikey/v1/locations/places/autocomplete?name=Parramatta&limit=5&website-sort=true&include-states=true&include-districts=true'
```

```json
{
  "candidates": [
    {
      "id": "bnsw_pt111",
      "coordinate": { "longitude": 151.0181, "latitude": -33.7917 },
      "gridcells": { "forecast": { "x": 655, "y": 224 } },
      "name": "Parramatta",
      "state": "NSW",
      "postcode": { "name": "2150", "description": null },
      "timezone": "Australia/Sydney",
      "type": "place",
      "feature_code": "place",
      "is_alpine": false
    }
  ]
}
```

This single response already carries the forecast grid cell, so for a
forecast-only integration you can go straight from a name to `/forecasts/daily`.

### 3.2 Place details — the lookup table

```
GET /locations/places/details/{type}/{id}
```

`{type}` is a path segment, not a fixed literal. Two are confirmed working:
`place` with a `place_id`, and `bom_stn` with a `bom_stn_num` — the latter
resolves a station straight to its coordinate, elevation, timezone and forecast
grid cell without going through a place:

```bash
curl 'https://api.bom.gov.au/apikey/v1/locations/places/details/bom_stn/66214'
```

| Param | Req | Notes |
|---|---|---|
| `filter` | no | Comma-separated, colon-delimited. Site uses `nearby_type:bom_stn`, and on the homepage `nearby_type:bom_stn,elevation:500,capability:SENSOR_TEMPERATURE_DB` |
| `radius` | no | Metres, for the nearby/nearest search. Site uses `100000` |
| `nearby_limit` | no | Max nearby stations returned. Site uses `10` |

```bash
curl 'https://api.bom.gov.au/apikey/v1/locations/places/details/place/bnsw_pt131?filter=nearby_type%3Abom_stn&radius=100000&nearby_limit=10'
```

Response (abridged):

```json
{
  "place": {
    "id": "bnsw_pt131",
    "name": "Sydney",
    "elevation": 38,
    "coordinate": { "longitude": 151.2048, "latitude": -33.8593 },
    "gridcells": { "forecast": { "x": 658, "y": 223 } },
    "postcode": { "name": "2000", "description": null },
    "timezone": "Australia/Sydney",
    "type": "place",
    "location_hierarchy": {
      "nearest": {
        "id": "66214",
        "name": "Sydney - Observatory Hill",
        "type": "bom_stn",
        "distance": 0,
        "elevation": 43.37,
        "coordinate": { "longitude": 151.2048, "latitude": -33.8593 },
        "timezone": "Australia/Sydney"
      },
      "nearby": [ "… same shape as nearest …" ],
      "locality_fcst":    { "aac": "NSW_PT131", "description": "Sydney" },
      "precis_fcst":      { "aac": "NSW_PT131", "description": "Sydney" },
      "public_district":  { "aac": "NSW_PW005", "description": "Metropolitan" },
      "metropolitan":     [{ "aac": "NSW_ME011", "description": "Eastern" }],
      "fire_district":    { "aac": "NSW_FW004", "description": "Greater Sydney Region" },
      "coast":            { "aac": "NSW_MW009", "description": "Sydney Enclosed Waters" },
      "marine_coast":     { "aac": "NSW_MW009", "description": "Sydney Enclosed Waters" },
      "tidal_location":   { "aac": "NSW_TP007", "description": "Sydney (Fort Denison)" },
      "tsunami_warn":     { "aac": "NSW_TW004", "description": "Sydney Coast" },
      "flood_watch_area": [{ "aac": "NSW_FL023", "description": "Parramatta River" }],
      "region":           [{ "aac": "AUS_FA001", "description": "Australia" }],
      "state":            { "abbrev": "NSW", "name": "NEW SOUTH WALES", "aac": "NSW_ST001" },
      "lga":              { "name": "17200", "description": "Sydney (C)" },
      "suburb":           { "name": "12619", "description": "Millers Point" },
      "capital_area":     "…",
      "national_landscape": "…",
      "post_code":        "…",
      "country":          "…",
      "coast_warn":       [ "…" ]
    }
  }
}
```

`location_hierarchy.nearest.id` is the `bom_stn_num` to use for observations.
The various `aac` values are what `forecasts/texts`, `forecasts/tidal` and
`warnings/list` expect.

### 3.3 Reverse lookup by coordinate — not usable

`GET /locations/places/search` exists and takes `coordinate`, `filter`, `radius`,
`website-sort`, `website-filter`, `nearby_limit`. **The accepted format of
`coordinate` could not be determined** — `lon,lat`, `lat,lon`, space-separated,
semicolon-separated, WKT `POINT(…)` and a 4-number bbox all return
`422 DMP-E-0001 "Invalid coordinates"`. The site declares the endpoint but never
calls it (its "Use location" button resolves through autocomplete instead).

Note the parameter is `coordinate` on the way in but the validator reports it as
`coordinates`; supplying the plural spelling instead gets
`400 "Required parameter 'coordinate' is not present."`, so the mismatch is
internal and not a way in.

**Working around it.** Nothing here needs the endpoint if all you want is a
forecast, because the forecast grid cell is a plain affine function of the
coordinate. Fitting the ten capitals and large towns gives:

```python
x = round((longitude - 111.9967) / 0.0595964)
y = round((latitude   + 44.9902) / 0.0499699)
```

That reproduces the `gridcells.forecast` returned by autocomplete for all ten
test points exactly (Sydney, Parramatta, Melbourne, Brisbane, Perth, Hobart,
Darwin, Adelaide, Cairns, Broome), and the latitude constants are recognisably
0.05° from 45°S. It is a regression fit against a small sample, not a published
constant: validate it more widely before relying on it, and note that being one
cell out is a ~6 km error.

This gets you `/forecasts/daily`, `/forecasts/1hourly` and `/forecasts/3hourly`
from a bare coordinate, and `/warnings/list?area_type=coordinate` already takes
one directly. It does **not** give you a `bom_stn_num` for observations or the
aacs for `/forecasts/texts` — those still require a `place_id`, so a
coordinate-only bootstrap cannot reach observations, precis text or fire danger.

One more location endpoint is declared in the front-end bundle and could not be
made to work: `/locations/places/exists` is routed but returns `422` for every
parameter set tried.

`/locations/places/list` **does** work, but only with an aac path segment —
`GET /locations/places/list/{aac}` returns `200` with every place inside that
area, each carrying its own coordinate, elevation and forecast grid cell.
Bare `/locations/places/list` is a `404`.

```bash
curl 'https://api.bom.gov.au/apikey/v1/locations/places/list/NSW_PW005'
```

```json
{ "aac": "NSW_PW005", "type": "public_district",
  "children": [ { "id": "o117157279", "elevation": 65.0,
                  "coordinate": { "longitude": 150.866703, "latitude": -33.869285 },
                  "gridcells": { "forecast": { "x": "…", "y": "…" } } } ] }
```

---

## 4. Forecasts

All forecast endpoints return the same envelope:

```json
{ "meta": { "issue_time_utc": "…", "issue_time_next_utc": "…", "local_timezone": "…" },
  "fcst": { "…": "…" } }
```

`issue_time_next_utc` tells you when it is worth polling again — use it instead of
a fixed interval.

### 4.1 Daily forecast (grid) — 8 days

```
GET /forecasts/daily/{grid_x}/{grid_y}?timezone={IANA tz}
```

`timezone` is **required** — omit it and you get `400 DMP-E-400 "Required request parameter 'timezone' … is not present"`.
It controls how the forecast is bucketed into local days.

```bash
curl 'https://api.bom.gov.au/apikey/v1/forecasts/daily/658/223?timezone=Australia%2FSydney'
```

```json
{
  "meta": {
    "issue_time_utc": "2026-09-07T18:00:15Z",
    "issue_time_next_utc": "2026-09-08T08:00:00Z",
    "local_timezone": "Australia/Sydney"
  },
  "fcst": {
    "daily": [
      {
        "date_utc": "2026-09-07T14:00:00Z",
        "atm": {
          "surf_air": {
            "temp_max_cel": 19.1,
            "temp_min_cel": 12.5,
            "precip": {
              "exceeding_10percentchance_total_mm": 2,
              "exceeding_25percentchance_total_mm": 0.5,
              "exceeding_50percentchance_total_mm": 0,
              "exceeding_75percentchance_total_mm": 0,
              "any_probability_percent": 37,
              "any_restofday_probability_percent": 2,
              "10mm_probability_percent": 0,
              "25mm_probability_percent": 0
            },
            "weather": { "icon_code": 11 },
            "radiation": {
              "uv_clear_sky_max_code": 6.018779,
              "uv_period_start": "2026-09-07T23:10:00Z",
              "uv_period_end": "2026-09-08T04:30:00Z"
            }
          }
        },
        "terr": { "surf_land": { "snow": {} } },
        "ocn":  { "surf_water": { "sea": {} } },
        "astro": { "sunrise_utc": null, "sunset_utc": null }
      }
    ]
  }
}
```

`fcst.daily` holds **8 entries** (today + 7). Note that `astro` here is usually
null — use `/forecasts/astro` for sun times. Empty objects (`snow: {}`, `sea: {}`)
are normal for places where those elements don't apply.

The rain fields are a probabilistic distribution rather than a single amount: the
site renders `exceeding_25percentchance_total_mm`–`exceeding_10percentchance_total_mm`
as its "0–1 mm" style range, and `any_probability_percent` as chance of rain.

### 4.2 Daily forecast for many places at once

```
GET /forecasts/daily-list/{YYYY-MM-DD}?place_id={id}&place_id={id}…
```

Takes **repeated `place_id`** (the site batches 10 per request) and a single local
date in the path. Returns one day per place, and unlike `/forecasts/daily` it
includes the precis text.

```bash
curl 'https://api.bom.gov.au/apikey/v1/forecasts/daily-list/2026-09-08?place_id=bnsw_pt131&place_id=bvic_pt042'
```

```json
{
  "meta": { "issue_time_utc": "2026-09-07T17:22:31Z", "issue_time_next_utc": "2026-09-08T08:00:00Z" },
  "fcst": [
    {
      "date_utc": "2026-09-07T14:00:00Z",
      "place_id": "bnsw_pt131",
      "timezone": "Australia/Sydney",
      "atm": { "surf_air": {
        "weather": {
          "icon_code": 4,
          "precis_text": "Possible morning shower.",
          "locality_text": "Partly cloudy. Medium chance of showers this morning. Winds southwesterly 15 to 25 km/h tending southerly in the morning then becoming light in the early afternoon."
        },
        "temp_max_cel": 19.1,
        "temp_min_cel": 12.5,
        "precip": { "any_probability_percent": 37, "exceeding_75percentchance_total_mm": 0, "exceeding_25percentchance_total_mm": 0.5 }
      } }
    },
    { "…": "…" }
  ]
}
```

`fcst` is a **plain array**, one entry per requested `place_id`, each carrying its
own `place_id` and `timezone` so you can match responses back to your request
rather than relying on order.

### 4.3 Hourly forecast — 8 days

```
GET /forecasts/1hourly/{grid_x}/{grid_y}?timezone={IANA tz}
```

`fcst` is an **array of 8 day objects**, each with a `1hourly` array — 24 entries
on a full day, fewer on the first (it starts at the next whole hour) and on the
last (it ends at the edge of the forecast horizon). A run observed at 07:20 local
gave day counts of 17, 24×6, 7 — 168 hours in total.

**`1hourly` carries no rain.** Its `atm.surf_air` holds exactly `temp_cel`,
`temp_apparent_cel`, `temp_dew_pt_cel`, `hum_relative_percent`, `wind` and
`radiation` — there is no `precip` key on any entry, and no `weather`/`icon_code`
either. Hourly rain probability and the hourly condition icon exist **only** in
`/forecasts/3hourly`. The two endpoints are complementary, not
higher- and lower-resolution versions of each other, so an hour-by-hour view with
both temperature and rain has to join them (see §4.4).

```json
{
  "meta": { "issue_time_utc": "2026-09-07T19:50:01Z", "issue_time_next_utc": "2026-09-08T06:00:00Z", "local_timezone": "Australia/Sydney" },
  "fcst": [
    {
      "date_utc": "2026-09-07T14:00:00Z",
      "1hourly": [
        {
          "time_utc": "2026-09-07T20:00:00Z",
          "atm": { "surf_air": {
            "temp_cel": 12.5,
            "temp_apparent_cel": 9,
            "temp_dew_pt_cel": 7.8,
            "hum_relative_percent": 73,
            "wind": {
              "dirn_10m_deg_t": 215.90001,
              "speed_10m_avg_mps": 4.444,
              "speed_10m_avg_kts": 10.7,
              "gust_speed_10m_max_mps": 8.231,
              "gust_speed_10m_max_kts": 16,
              "mixing_height_m": 690
            },
            "radiation": { "uv_clear_sky_code": 0 }
          } }
        }
      ]
    }
  ]
}
```

### 4.4 Three-hourly forecast — 8 days

```
GET /forecasts/3hourly/{grid_x}/{grid_y}?timezone={IANA tz}
```

Same structure — `fcst` is an array of 8 day objects — with the inner array named
`3hourly`, 8 blocks on a full day (56 in a run). This is the richer payload for
*conditions*: it carries rain, cloud, the split weather icons, fire fuel dryness
and sea state. It carries **no temperature and no wind**, which is exactly what
`1hourly` has and this does not — see the note in §4.3:

```json
{
  "start_time_utc": "2026-09-07T18:00:00Z",
  "end_time_utc": "2026-09-07T21:00:00Z",
  "atm": { "surf_air": {
    "precip": {
      "exceeding_10percentchance_total_mm": 0.9,
      "exceeding_25percentchance_total_mm": 0.3,
      "exceeding_50percentchance_total_mm": 0,
      "precip_any_probability_percent": 35
    },
    "radiation": { "uv_clear_sky_code": 0 },
    "weather": {
      "icon_code": 11,
      "icon_rain_code": 10,
      "icon_fog_code": 0,
      "icon_frost_code": 0,
      "icon_snow_code": 0,
      "icon_thunderstorm_code": 0
    },
    "cloud_amt_avg_percent": 53
  } },
  "terr": { "surf_land": {
    "fire_danger": { "forest_fuel_dryness_factor_avg_code": 7.4 },
    "snow": {}
  } },
  "ocn": { "surf_water": {
    "wave":  { "height_wind_m": 0.4, "total_height_m": 0.4 },
    "swell": { "1st_dirn_deg_t": 0, "1st_height_m": 0, "2nd_dirn_deg_t": 77.9, "2nd_height_m": 0.01 }
  } }
}
```

Note `precip_any_probability_percent` here vs `any_probability_percent` in the
daily payload — the naming is not consistent between endpoints.

### 4.5 Text forecasts

```
GET /forecasts/texts?aac={aac}&aac={aac}…&timezone={IANA tz}
```

Repeated `aac`. The site requests the whole set for a location at once, e.g.
`NSW_PW005` (public district), `NSW_FW004` (fire), `NSW_MW009` (coastal waters),
`NSW_FA001` (state), `NSW_ME011` (metropolitan), `NSW_PT131` (town).

Returns one `fcst.daily[]` with a slot per text type; irrelevant slots are `null`,
so merge across the aacs you asked for. Note it returns **7 days**, one fewer than
the 8 of `/forecasts/daily` — don't zip the two by index without checking.

This endpoint is also the **only** source of the fire danger rating (§4.4's
3-hourly `fire_danger` is fuel dryness, a different quantity). Ask with the
`fire_district` aac from place details and read
`terr.surf_land.fire_danger`:

```json
{
  "meta": { "issue_time_utc": "2026-09-07T18:57:37Z", "issue_time_next_utc": "2026-09-08T06:00:00Z", "local_timezone": "Australia/Sydney" },
  "fcst": {
    "summary": {
      "region_text": null, "region_coastal_text": null, "sub_region_text": null,
      "sub_region_coastal_text": null, "public_district_text": null,
      "seas_text": null, "coast_text": null, "locality_text": null
    },
    "daily": [{
      "date_utc": "2026-09-07T14:00:00Z",
      "atm": { "surf_air": {
        "weather": {
          "precis_text": "Possible morning shower.",
          "locality_text": "Partly cloudy. Medium chance of showers…",
          "region_text": null, "public_district_text": null,
          "metropolitan_text": null, "seas_text": null, "coast_text": null
        },
        "radiation": { "advice_summary": { "locality_text": "Sun protection 9:10am to 2:30pm…", "metropolitan_text": null, "public_district_text": null } },
        "wind": { "coastal": { "coast_text": null }, "warning_summary": { "coast_text": null } },
        "heatwave": { "country_text": null, "link_map_image": null },
        "tropical_system_situation": { "coast_text": null }
      } },
      "ocn": { "…": "…" },
      "terr": { "surf_land": {
        "fire_danger": {
          "rating": {
            "fire_district_code": "Moderate",
            "public_district_code": null,
            "fire_behaviour_index": 15
          },
          "locality_text": "Moderate",
          "metropolitan_text": null, "public_district_text": null, "region_text": null
        }
      } }
    }]
  }
}
```

`rating.fire_district_code` is the rating word under the Australian Fire Danger
Rating System (`Moderate`, `High`, `Extreme`, …) and `rating.fire_behaviour_index`
is the numeric index behind it — the latter has no equivalent in the old API.

### 4.6 Sun times

```
GET /forecasts/astro/{longitude}/{latitude}
```

Note the order: **longitude first**. 8 days, no query params.

```bash
curl 'https://api.bom.gov.au/apikey/v1/forecasts/astro/151.2/-33.85'
```

```json
{
  "meta": { "local_timezone": "Australia/Sydney" },
  "fcst": { "daily": [
    { "date_utc": "2026-09-07T14:00:00Z",
      "astro": { "sunrise_utc": "2026-09-07T20:04:46Z", "sunset_utc": "2026-09-08T07:41:55Z" } }
  ] }
}
```

No moon phase or civil twilight is returned.

### 4.7 Tides

```
GET /forecasts/tidal/{aac}
```

Use `location_hierarchy.tidal_location.aac` from place details (e.g. `NSW_TP007`).
8 days, no query params.

```json
{
  "meta": { "issue_time_utc": "2025-03-26T06:10:24Z", "local_timezone": "Australia/Sydney" },
  "fcst": { "daily": [
    { "date_utc": "2026-09-07T14:00:00Z",
      "tide": [ { "height_m": 1.31, "datetime_utc": "2026-09-07T19:57:00Z", "type": "high" } ] }
  ] }
}
```

`meta.issue_time_utc` on tides is the publication date of the tidal prediction
tables, not a recent run time — don't treat it as staleness.

---

## 5. Observations

All observation endpoints take `bom_stn_num` (not a place id), and all of them
sit under the `atm/surf_air` element path.

### 5.1 Latest observation for one station

```
GET /observations/latest/{bom_stn_num}/atm/surf_air?include_qc_results=false
```

`include_qc_results` is required (`true` adds QC flags to each value).

```bash
curl 'https://api.bom.gov.au/apikey/v1/observations/latest/66214/atm/surf_air?include_qc_results=false'
```

```json
{
  "stn": {
    "identity": {
      "bom_stn_num": 66214,
      "bom_stn_name": "Sydney - Observatory Hill",
      "wmo_stn_id": 94768,
      "wigos_stn_id": null,
      "river_stn_id": null,
      "ht_above_msl": 43.37,
      "ht_barometer": 43.9
    },
    "location": { "lat_dec_deg": -33.8593, "long_dec_deg": 151.2048, "timezone": "Australia/Sydney" }
  },
  "obs": {
    "datetime_utc": "2026-09-07T21:00:00Z",
    "temp": {
      "dry_bulb_1min_cel": 12.2,
      "apparent_1min_cel": 7.66,
      "dew_pnt_1min_cel": 7.51,
      "wet_bulb_1min_avg_cel": 9.93,
      "wet_bulb_globe_sun_cel": 14.93,
      "wet_bulb_globe_shade_cel": 10.61,
      "wet_bulb_depression_cel": 2.27,
      "dry_bulb_max_cel": 12.3,
      "dry_bulb_max_time_utc": "2026-09-07T21:00:00Z",
      "dry_bulb_min_cel": 11.6,
      "dry_bulb_min_time_utc": "2026-09-07T20:21:00Z",
      "rel_hum_percent": 73
    },
    "pres": { "stn_lvl_hpa": null, "msl_hpa": 1026.6, "qnh_hpa": 1026.6 },
    "wind": {
      "speed_10m_mps": 5.247,
      "dirn_10m_ord": "W",
      "gust_speed_10m_mps": 7.717,
      "gust_dirn_10m_deg_t": 165,
      "gust_speed_10m_max_mps": 14.404,
      "gust_10m_max_utc": "2026-09-07T14:29:00Z",
      "run_2m_total_m": null
    },
    "precip": {
      "since_0900lct_total_mm": 6.2,
      "since_0000lct_total_mm": 0.2,
      "24h_0900lct_total_mm": 6.2,
      "10min_total_mm": 0,
      "1h_total_mm": 0,
      "24h_total_mm": null
    },
    "visibility": { "horiz_m": null },
    "cloud": {
      "total_cover_amt_text": null,
      "low_layer_cover_amt_okta": null, "low_layer_height_m": null,
      "med_layer_cover_amt_okta": null, "med_layer_height_m": null,
      "high_layer_cover_amt_okta": null, "high_layer_height_m": null,
      "base_ht_s1_m": null, "base_ht_s2_m": null, "base_ht_s3_m": null,
      "base_ht_s4_m": null, "base_ht_s5_m": null
    }
  }
}
```

That is a real response, nulls included: an automatic weather station reports only
the elements it is instrumented for, so `visibility`, `cloud` and several `pres`
and `wind` fields are commonly `null` even at a major site like Observatory Hill.
Omitting `include_qc_results` is a `400`, not a default.

Field-name gotchas versus the old API: temperature is `temp.dry_bulb_1min_cel`
(not `temp`), "feels like" is `temp.apparent_1min_cel`, humidity lives under
`temp.rel_hum_percent`, wind speed is in **m/s** and wind direction is an
**ordinal string** (`"W"`), and rain since 9am is `precip.since_0900lct_total_mm`.

### 5.2 Latest for many stations

```
GET /observations/latest-list/atm/surf_air?bom_stn_num={n}&bom_stn_num={n}…&include_qc_results=false
```

Returns `{ "obs_list": [ { "stn": …, "obs": … } ] }` with the same per-station
shape as above. The site uses this for its 10-station district tables.

### 5.3 Recent observations (time series)

```
GET /observations/recent/{bom_stn_num}/atm/surf_air
      ?from_time_utc={ISO}&to_time_utc={ISO}&duration={PT1M|PT30M}&include_qc_results=false
```

**All four query parameters are required.** `duration` is an ISO 8601 duration and
only `PT1M` and `PT30M` are accepted (the front-end's own type is
`'PT30M' | 'PT1M'`).

```bash
curl 'https://api.bom.gov.au/apikey/v1/observations/recent/66214/atm/surf_air?from_time_utc=2026-09-07T15:00:00Z&to_time_utc=2026-09-07T21:00:00Z&duration=PT30M&include_qc_results=false'
```

```json
{
  "stn": { "…": "…" },
  "obs_recent": [
    {
      "date": "2026-09-08",
      "astro": { "sunrise_utc": "2026-09-07T20:04:46Z", "sunset_utc": "2026-09-08T07:41:53Z" },
      "obs": [ { "datetime_utc": "2026-09-07T15:00:00Z", "temp": {…}, "pres": {…}, "wind": {…}, "precip": {…}, "visibility": {…}, "cloud": {…} } ]
    }
  ]
}
```

Results are grouped by **local** date, each group carrying that day's sun times.
This is the closest thing the new API has to observation history; there is no
`/observations/history` or `/observations/timeseries` (both 404).

### 5.4 Area extremes

```
GET /observations/extremes/latest/atm/surf_air?aac={aac}
GET /observations/extremes/latest/atm/surf_air?bom_stn_num={n}
```

Hottest/coldest across an area, with the station that recorded it:

```json
{ "obs": { "temp": {
  "dry_bulb_max_cel": 13.6,
  "dry_bulb_max_time_utc": "2026-09-07T21:00:00Z",
  "dry_bulb_max_bom_stn_num": 67105,
  "dry_bulb_max_bom_stn_name": "Richmond",
  "dry_bulb_max_bom_stn_timezone": "Australia/Sydney",
  "dry_bulb_min_cel": 8.7,
  "dry_bulb_min_time_utc": "2026-09-07T19:59:00Z",
  "…": "…"
} } }
```

### 5.5 Declared but not routed

The front-end bundle also names `observations/latest-heights/terr/surf_wtr`
(river height bulletin) and `observations/latest-{1,3,24}hourly-rainfall/atm/surf_air`.
Every guessed form of these returned `404 No Mapping Rule matched` on the public
gateway — they are presumably reachable with parameters the site doesn't yet use,
or gated internally.

---

## 6. Warnings

### 6.1 List

```
GET /warnings/list?area_type=coordinate&area_code={lon},{lat}
GET /warnings/list?area_type=aac&area_code={aac}
GET /warnings/list?warning_type={type}&warning_type={type}…
```

- `area_code` for `coordinate` is **`longitude,latitude`** (URL-encode the comma).
- **`area_code` is single-valued.** Repeating it fails validation
  (`must match ^[a-zA-Z0-9]+_?[a-zA-Z0-9]+$` against the joined value) — issue one
  request per area, as the site does.
- `warning_type` *is* repeatable and is used without any area (the site polls
  `warning_type=WTCWW&warning_type=WOW` for tropical-cyclone and ocean wind warnings).

```bash
curl 'https://api.bom.gov.au/apikey/v1/warnings/list?area_type=coordinate&area_code=151.2%2C-33.85'
```

```json
{
  "warnings": [
    {
      "id": "IDN20400",
      "title": "Marine Wind Warning",
      "sub_title": "New South Wales",
      "type": "WMS",
      "issue_type": "Update",
      "severity_code": ["STR", "CAN"],
      "area_state_code": "NSW",
      "issue_datetime_utc": "2026-09-07T18:00:00Z",
      "expires_datetime_utc": "2026-09-09T14:00:00Z",
      "area_summary": null,
      "phenomena_summary": null,
      "link_details": null,
      "disturbance_name": null,
      "disturbance_type": null,
      "incident_refs": null,
      "dist_title": null
    }
  ]
}
```

State-level aacs used by the site's warnings page: `NSW_FA001`, `VIC_FA001`,
`QLD_FA001`, `WA_FA001`, `SA_FA001`, `TAS_FA001`, `NT_FA001`, `NSW_PW017` (ACT),
`AAT_FA001` (Antarctic), `MI_TW001` (Macquarie Island).

### 6.2 Count

```
GET /warnings/count?area_type=aac&area_code={aac}&area_code={aac}…
```

Here `area_code` **is** repeatable. Cheap way to drive a badge without pulling
every warning body:

```json
[ { "area_code": "NSW_FA001", "count": 4 },
  { "area_code": "VIC_FA001", "count": 6 },
  { "area_code": "QLD_FA001", "count": 0 } ]
```

### 6.3 Warning detail

```
GET /warnings/warning/{warning_id}
```

Note the doubled path segment — `/warnings/{id}` is a 404.

```json
{
  "ref": { "product": { "number": "IDN20400", "type": "W", "link": null },
           "status": "O", "service": "WSM", "sub_service": "WMS", "type": "WMS" },
  "meta": {
    "source": { "name": "Australian Government Bureau of Meteorology", "office": "NSWRO", "region": "New South Wales",
                "copyright": "http://www.bom.gov.au/…", "disclaimer": "http://www.bom.gov.au/…" },
    "issue_datetime_utc": "2026-09-07T18:00:00Z",
    "issue_next_datetime_utc": "2026-09-08T00:00:00Z",
    "valid_begin_datetime_utc": "2026-09-07T18:00:00Z",
    "valid_end_datetime_utc": "2026-09-09T13:59:59Z"
  },
  "warning": {
    "id": "IDN20400",
    "title": "Marine Wind Warning",
    "sub_title": "New South Wales",
    "area_state_code": "NSW",
    "issue_type": "Update",
    "scope": "Public",
    "onset_datetime_utc": "2026-09-07T18:00:00Z",
    "expires_datetime_utc": "2026-09-09T14:00:00Z",
    "next_issue": "The next marine wind warning will be issued by …",
    "postamble1": "Check the latest Coastal Waters Forecast …",
    "info": [
      {
        "type": "WMS",
        "category": "Met",
        "onset_datetime_utc": "2026-09-07T18:00:00Z",
        "end_datetime_utc": "2026-09-09T13:59:59Z",
        "summary": "<p>Strong Wind Warning for …</p>",
        "for_text": "for the following areas:",
        "is_hazard": "false",
        "area": [ { "geocode": [ { "type": "aac:region", "code": "NSW_FA001", "name": "New South Wales" } ] } ]
      }
    ]
  }
}
```

`warning.info[].summary` is **HTML**, and `is_hazard` is a *string* `"false"`, not
a boolean.

Full bulletin text for a product id is available separately as plain text at
`GET /products/{product_id}` (e.g. `IDN10033`) — that endpoint serves forecast and
bulletin products, not warnings (`/products/IDN20400` → 404).

---

## 7. Weather icon codes

`weather.icon_code` (daily, 3-hourly and daily-list) maps to the site's icon set as
follows. Codes 5 and 7 are unused placeholders in the front-end.

| Code | Day icon | Night icon |
|---|---|---|
| 1 | sunny | clear-night |
| 2 | sunny | clear-night |
| 3 | mostly-sunny | mostly-clear-night |
| 4 | cloudy | cloudy-night |
| 5 | *(unused)* | *(unused)* |
| 6 | haze | haze-night |
| 7 | *(unused)* | *(unused)* |
| 8 | light-rain | light-rain-night |
| 9 | wind | wind-night |
| 10 | fog | fog-night |
| 11 | showers | showers-night |
| 12 | rain | rain-night |
| 13 | dust | dust-night |
| 14 | frost | frost-night |
| 15 | snow | snow-night |
| 16 | storms | storms-night |
| 17 | light-showers | light-showers-night |
| 18 | heavy-showers | heavy-showers-night |
| 19 | cyclone | cyclone-night |

Code 3 also has alternates (`partly-cloudy` / `partly-cloudy-night`) that the site
selects on cloud amount. Human-readable text comes with the payload
(`weather.precis_text`), so you generally don't need a code→phrase table.

The 3-hourly payload additionally splits the condition into
`icon_rain_code`, `icon_fog_code`, `icon_frost_code`, `icon_snow_code` and
`icon_thunderstorm_code` alongside the combined `icon_code`.

---

## 8. Worked example

Everything a typical integration needs, for "Sydney":

```bash
BASE=https://api.bom.gov.au/apikey/v1

# 1. name -> place_id (+ grid cell, straight away)
curl "$BASE/locations/places/autocomplete?name=Sydney&limit=5&website-sort=true"

# 2. place_id -> grid cell, nearest station, aacs
curl "$BASE/locations/places/details/place/bnsw_pt131?filter=nearby_type%3Abom_stn&radius=100000&nearby_limit=10"
#    -> gridcells.forecast = 658/223
#    -> location_hierarchy.nearest.id = 66214
#    -> location_hierarchy.precis_fcst.aac = NSW_PT131
#    -> location_hierarchy.tidal_location.aac = NSW_TP007

# 3. current conditions
curl "$BASE/observations/latest/66214/atm/surf_air?include_qc_results=false"

# 4. 7-day forecast
curl "$BASE/forecasts/daily/658/223?timezone=Australia%2FSydney"

# 5. hourly detail
curl "$BASE/forecasts/1hourly/658/223?timezone=Australia%2FSydney"
curl "$BASE/forecasts/3hourly/658/223?timezone=Australia%2FSydney"

# 6. worded forecast
curl "$BASE/forecasts/texts?aac=NSW_PT131&aac=NSW_PW005&timezone=Australia%2FSydney"

# 7. sun times
curl "$BASE/forecasts/astro/151.2/-33.85"

# 8. warnings for the point
curl "$BASE/warnings/list?area_type=coordinate&area_code=151.2%2C-33.85"
curl "$BASE/warnings/warning/IDN20400"
```

Cache steps 1–2 permanently per configured location; only steps 3–8 need polling.

---

## 9. Migrating from `api.weather.bom.gov.au/v1`

| Old | New |
|---|---|
| `GET /locations?search={lat},{lon}` | `GET /locations/places/autocomplete?name=…` (no working coordinate lookup — see §3.3) |
| `GET /locations?search={postcode}` | `GET /locations/places/autocomplete?name={postcode}` |
| `GET /locations/{geohash}` | `GET /locations/places/details/place/{place_id}` |
| `GET /locations/{geohash}/observations` | `GET /observations/latest/{bom_stn_num}/atm/surf_air?include_qc_results=false` |
| `GET /locations/{geohash}/forecasts/daily` | `GET /forecasts/daily/{x}/{y}?timezone=…` (+ `/forecasts/texts` for the wording) |
| `GET /locations/{geohash}/forecasts/hourly` | `GET /forecasts/1hourly/{x}/{y}?timezone=…` **and** `/forecasts/3hourly/…` — both, see below |
| `daily[].fire_danger` | `GET /forecasts/texts?aac={fire_district_aac}` → `terr.surf_land.fire_danger` |
| `daily[].now` (now/later) | *no equivalent* |
| `GET /locations/{geohash}/warnings` | `GET /warnings/list?area_type=coordinate&area_code={lon},{lat}` |
| `GET /warnings/{id}` | `GET /warnings/warning/{id}` |
| — | `GET /observations/recent/…` (time series), `/observations/extremes/latest/…`, `/forecasts/astro/…`, `/forecasts/tidal/…`, `/forecasts/daily-list/…` |

Behavioural differences worth planning for:

- **No geohash.** One identifier became four; `places/details` is the bridge.
- **No `data` / `metadata` envelope.** Responses use `meta` + `fcst`, or bare
  `stn` + `obs`.
- **Forecast and observation are decoupled.** The old API gave you observations
  for a location; now you resolve a station first, and the nearest station may be
  tens of kilometres away (`location_hierarchy.nearest.distance`, in metres).
- **Units changed.** Observed wind is m/s (with knots alongside in forecasts);
  observed wind direction is an ordinal string.
- **Rain is a distribution**, not `amount.min`/`amount.max`.
- **`timezone` is mandatory** on the grid forecast endpoints.
- **`fcst` is an array everywhere** — `daily`, `daily-list`, `1hourly` and
  `3hourly` all return plain JSON arrays. (`daily-list` entries carry their own
  `place_id`, so match on that rather than on position.)
- **Hourly rain moved.** The old `/forecasts/hourly` gave temperature, wind *and*
  rain on one hourly record. In the new API `1hourly` has no `precip` and no
  icon, and `3hourly` has no temperature and no wind; reproducing the old record
  means joining the two on time.
- **No `now`/`later` block.** The old daily day-0 `now` object (`now_label`,
  `temp_now`, `later_label`, `temp_later`, `is_night`) has no counterpart. The
  underlying min/max are still there, but the "which comes next" logic and the
  day/night flag have to be derived locally.
- **Fire danger moved** from the daily forecast to `/forecasts/texts` under the
  fire-district aac (§4.5), and gains `fire_behaviour_index`.
- **UV category is not a field.** The old `uv.category` (`"high"`) is now only the
  numeric `uv_clear_sky_max_code`, plus a prose sentence in
  `radiation.advice_summary.locality_text` ("UV Index predicted to reach 5
  [Moderate]"). Bucket the number yourself rather than parsing the sentence.
- Poll on `meta.issue_time_next_utc` rather than a fixed schedule.

---

## 10. Caveats

- This is an internal API for bom.gov.au. It carries no version guarantee, no
  published contract, and BOM has not invited third-party use. It can change or
  start requiring the `X-API-Key` header at any time — the plumbing for that is
  already in the front-end.
- The old `api.weather.bom.gov.au/v1` host still returns live data as at
  10 September 2026, and although the website no longer uses it, **it is the live
  backend for the current BOM Weather mobile app** (`au.gov.bom.metview` 6.14.0) —
  see §11. It is therefore in active production use, not merely still answering.
- The new host is **bot-managed and the old one is not** (§1). Today the filter
  only rejects the default `curl` User-Agent, but Akamai Bot Manager rules are
  tuned server-side and without notice. Any client moving to `api.bom.gov.au`
  should send a stable, identifying User-Agent and treat an HTML body with a
  4xx status as "blocked", distinct from a JSON error.
- **There is no rain-arrival or precipitation-onset field** anywhere in the new
  API — no `arriv*`, `onset*` or "rain starting" element in any forecast
  endpoint. The closest available signals are
  `daily[0].precip.any_restofday_probability_percent` and the per-block
  `precip_any_probability_percent` in `/forecasts/3hourly`, from which the first
  block over a chosen threshold gives an arrival time at 3-hour granularity.
  The old API has no such field either, and the mobile app's "rain approaching"
  alert does not come from an API at all (§11).
- Empty objects and `null`s are common and meaningful (element not applicable at
  that place, or not yet issued). Handle them rather than treating them as errors.
- Naming is inconsistent across endpoints (`any_probability_percent` vs
  `precip_any_probability_percent`; `warnings/warning/{id}` vs `warnings/list`);
  don't infer a path or field name — probe it, the error messages are explicit.
- BOM material is licensed CC BY 4.0 with attribution requirements; check
  http://www.bom.gov.au/other/copyright.shtml before redistributing.

---

## 11. What the mobile app uses

From the Retrofit path annotations in `au.gov.bom.metview` 6.14.0. Retrofit
requires string literals, so this is the app's complete HTTP surface:

```
locations/{geohash}
locations/{geohash}/forecasts/daily
locations/{geohash}/forecasts/hourly
locations/{geohash}/observations
locations/{geohash}/warnings
```

All five are on `https://api.weather.bom.gov.au/v1` — the old geohash API. The
app does not call `api.bom.gov.au` at all.

One further endpoint on that host is undocumented but live:
`GET /v1/app-version-support` returns `200` with
`data.{latest_version, active_from_version, deprecated{from_version, end_date, heading, text}}`.

**There is no rain-nowcast endpoint on either API.** The app's "rain approaching"
notification (offering "up to 30 minutes notice") is not fetched:

- it is gated by a Firebase Remote Config flag, `RAIN_NOTIFICATION`;
- it is delivered by Firebase Cloud Messaging (`subscribeToTopic`), so the text
  is composed server-side;
- subscriptions are per saved location × alert type, in two families —
  `warnings/...` and `storm-whisperer/...` (the latter covering rain, hail,
  frost, fire weather, storm tide, haze and bushwalker alerts). Neither family's
  path resolves on `api.weather.bom.gov.au`; the host is supplied at runtime.
- the radar imagery is Mapbox-hosted on BOM's own account (style
  `mapbox://styles/bom-dc-prod/…`, tilesets `BOM-RainRateStaticReference-Nowcast`
  and `-Observation`), with tile URLs handed to the client at runtime.

Nothing here is pollable by a third party: the rain nowcast is pushed, and its
tiles are billed to BOM's Mapbox account.
