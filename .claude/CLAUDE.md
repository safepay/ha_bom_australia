# Bureau of Meteorology (`ha_bom_australia`)

A Home Assistant custom integration, distributed via HACS, that surfaces
Australian Bureau of Meteorology weather data as a weather entity plus
observation, forecast and warning entities.

## Git conventions

**Never add a Claude signature to commits or pull requests.** Specifically, do
not append `Co-Authored-By: Claude ...`, `🤖 Generated with [Claude Code]`, or
any equivalent attribution trailer or footer. Commit messages and PR bodies
should read as if written by the maintainer.

- Never commit directly to `main`. Branch first, then merge via pull request.
- Branch names: `<type>/<kebab-case-summary>`, e.g. `fix/weather-daily-partial-day`.
- Commit subjects use conventional prefixes: `fix:`, `feat:`, `chore:`.
- Write a body when the *why* isn't obvious from the subject; skip it for trivia.

## Layout

```
custom_components/ha_bom_australia/
├── __init__.py       # setup/unload, BomDataUpdateCoordinator, config entry migration
├── config_flow.py    # ConfigFlow + BomOptionsFlow (location search, entity selection)
├── const.py          # DOMAIN, CONF_* keys, condition/icon maps, SensorEntityDescriptions
├── weather.py        # WeatherBase -> BomWeather
├── sensor.py         # SensorBase -> Observation/Forecast/NowLater/Warnings sensors
├── binary_sensor.py  # BomWarningSensor
└── PyBoM/            # self-contained BOM API client (no external SDK)
    ├── collector.py  # Collector: fetches and reshapes the five endpoints
    ├── const.py      # URLs, MAP_MDI_ICON, MAP_UV, apply_day_night()
    └── helpers.py    # flatten_dict, geohash_encode
```

`api doc/` holds notes on the upstream BOM API. There is no test suite.

## How it works

- **Config flow only** — no YAML. `CONFIG_SCHEMA` is `config_entry_only_config_schema`.
  Config entries are at version 2; `async_migrate_entry` upgrades v1's
  `forecasts_basename` to `weather_name`.
- `BomDataUpdateCoordinator` polls every 5 minutes with a 60-second debouncer.
  One `Collector.async_update()` hits all five BOM endpoints per cycle
  (`locations`, `observations`, `forecasts/daily`, `forecasts/hourly`, `warnings`).
- `Collector._fetch_with_retry` retries 3 times with exponential backoff and
  falls back to a per-endpoint in-memory cache, so a BOM outage degrades rather
  than blanking entities.
- Entity IDs are built from `entity_prefix` (default `bom_<weather_name>`):
  `weather.<prefix>`, `sensor.<prefix>_<observation>`,
  `sensor.<prefix>_<day>_<forecast>`, `binary_sensor.<prefix>_warning_<type>`.
  `async_unload_entry` prunes registry entries that no longer match the options,
  so changing entity naming logic orphans users' entities — tread carefully.

## Gotchas that have caused bugs before

- **BOM returns `null` constantly.** `temp_min`, `temp_max`, `fire_danger` and
  `fire_danger_category` for today are persisted to a HA `Store` and restored
  when the API omits them. Guard every field read; assume nothing is present.
- **The daily forecast's last day is partial** (only an overnight min, with
  `temp_max` and icon fields null). It is dropped so the weather card shows
  complete days only.
- **`sunny` vs `clear`** — BOM reports the same clear sky as `sunny` by day and
  `clear` by night. `apply_day_night()` in `PyBoM/const.py` reconciles the
  descriptor; icons regress here if it's bypassed.
- **Geohash length is inconsistent.** `observations` and `forecasts/hourly`
  require exactly 6 characters, while daily and warnings accept 6 or 7. BOM's
  postcode search returns 7, so `Collector` truncates to 6.
- Icon descriptors map through `MAP_MDI_ICON` (Material icons) *and*
  `MAP_CONDITION` (HA weather states). A new BOM descriptor needs both.

## Versioning and releases

The version lives in exactly one place: `version` in `manifest.json`. Don't edit
it by hand and don't create tags manually — run the **Release** workflow
(`.github/workflows/release.yml`), which bumps the manifest, tags the commit and
creates the GitHub release that HACS reads. See `.github/RELEASING.md`.

Note that HACS shows release notes in Home Assistant's update dialog,
cumulatively across every release between the user's installed version and the
latest, so notes need to read well standalone.

## Validation

Hassfest and HACS validation run on every push and pull request
(`.github/workflows/hassfest.yml`, `validate.yml`). Both must be green before a
release is cut. Keep `manifest.json` keys in the order hassfest expects.
