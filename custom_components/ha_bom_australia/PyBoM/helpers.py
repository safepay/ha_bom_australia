"""Helpers functions for PyBom."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

# BOM's rain forecast resolves to 3-hour blocks, aligned to UTC.
RAIN_CHUNK_HOURS = 3


@dataclass(frozen=True)
class RainChunk:
    """One 3-hourly block of BOM's rain forecast.

    ``at_least`` and ``up_to`` are BOM's rain amount range in mm: the amounts
    with a 50% and a 25% chance of being exceeded.
    """

    start: datetime
    end: datetime
    chance: int | float | None
    at_least: int | float | None
    up_to: int | float | None
    condition: str | None


def _number(value: Any) -> int | float | None:
    """Return the value if it is a number, otherwise None."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def _chunk_end(hour: dict[str, Any]) -> datetime | None:
    """Return when the 3-hourly block an hourly entry belongs to ends.

    ``next_three_hourly_forecast_period`` carries it. Older responses put a word
    such as "tonight" there instead, so when it is not a timestamp the block is
    worked out from the entry's own time, blocks being aligned to UTC.
    """
    try:
        return parse_iso_datetime(hour.get("next_three_hourly_forecast_period"))
    except ValueError:
        pass
    try:
        time = parse_iso_datetime(hour.get("time")).astimezone(timezone.utc)
    except ValueError:
        return None
    start = time.replace(
        hour=time.hour - time.hour % RAIN_CHUNK_HOURS, minute=0, second=0, microsecond=0
    )
    return start + timedelta(hours=RAIN_CHUNK_HOURS)


def rain_chunks(hours: Any, now: datetime) -> list[RainChunk]:
    """Group the hourly forecast into the 3-hourly blocks its rain belongs to.

    BOM repeats one rain chance and amount across the three hours of a block, so
    the block is the finest resolution its rain forecast has. A block's start is
    taken as three hours before its end rather than from the first entry present,
    because BOM drops hours as they pass and the current block's first hour is
    usually gone. Blocks that have already ended are dropped: the collector keeps
    serving its last good response while BOM is unreachable, and that ages.
    """
    chunks: list[RainChunk] = []
    if not isinstance(hours, list):
        return chunks
    for hour in hours:
        if not isinstance(hour, dict):
            continue
        end = _chunk_end(hour)
        if end is None or end <= now:
            continue
        if chunks and chunks[-1].end == end:
            # Another hour of a block already read; it repeats the same figures.
            continue
        at_least = _number(hour.get("rain_amount_min"))
        up_to = _number(hour.get("rain_amount_max"))
        chunks.append(
            RainChunk(
                start=end - timedelta(hours=RAIN_CHUNK_HOURS),
                end=end,
                chance=_number(hour.get("rain_chance")),
                at_least=at_least,
                # BOM leaves the upper figure null when the range is one value.
                up_to=up_to if up_to is not None else at_least,
                condition=hour.get("icon_descriptor"),
            )
        )
    return chunks


def rain_event(chunks: list[RainChunk], threshold: int | float) -> list[RainChunk]:
    """Return the next run of consecutive wet blocks.

    A block is wet at a chance of ``threshold`` or more, unless BOM forecasts no
    rain amount for it. Its upper figure is the amount with a 25% chance of
    being exceeded, so below a 25% chance it is always 0: those are the edges of
    a system, where a shower is possible but no measurable rain is expected, and
    counting them reports rain arriving with nothing to say how much. A missing
    amount is unknown rather than none, so it does not rule a block out.

    The run starts at the first wet block, which may be the one under way, and
    stops at the first block that is not wet or at a gap in the forecast.
    Empty when no block is wet.
    """
    event: list[RainChunk] = []
    for chunk in chunks:
        wet = (
            chunk.chance is not None
            and chunk.chance >= threshold
            and chunk.up_to != 0
        )
        if event and (not wet or chunk.start != event[-1].end):
            break
        if wet:
            event.append(chunk)
    return event


def parse_iso_datetime(value: Any) -> datetime:
    """Parse an ISO 8601 timestamp, defaulting to UTC when no offset is given.

    Raises ValueError if the value is not a valid timestamp, including when it
    is not a string at all. BOM omits timestamp fields routinely, so callers
    guarding with `except ValueError` need a null to land there too rather than
    escaping as the TypeError datetime.fromisoformat would raise.
    """
    if not isinstance(value, str):
        raise ValueError(f"not a timestamp string: {value!r}")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed

def flatten_dict(keys: list[str], dict: dict[str, Any]) -> dict[str, Any]:
    """Flatten nested dictionary keys."""
    for key in keys:
        if dict[key] is not None:
            flatten = dict.pop(key)
            for inner_key, value in flatten.items():
                dict[key + "_" + inner_key] = value
    return dict

def geohash_encode(latitude: float, longitude: float, precision: int = 6) -> str:
    """Encode latitude/longitude to geohash string."""
    base32 = '0123456789bcdefghjkmnpqrstuvwxyz'
    lat_interval = (-90.0, 90.0)
    lon_interval = (-180.0, 180.0)
    geohash = []
    bits = [16, 8, 4, 2, 1]
    bit = 0
    ch = 0
    even = True
    while len(geohash) < precision:
        if even:
            mid = (lon_interval[0] + lon_interval[1]) / 2
            if longitude > mid:
                ch |= bits[bit]
                lon_interval = (mid, lon_interval[1])
            else:
                lon_interval = (lon_interval[0], mid)
        else:
            mid = (lat_interval[0] + lat_interval[1]) / 2
            if latitude > mid:
                ch |= bits[bit]
                lat_interval = (mid, lat_interval[1])
            else:
                lat_interval = (lat_interval[0], mid)
        even = not even
        if bit < 4:
            bit += 1
        else:
            geohash += base32[ch]
            bit = 0
            ch = 0
    return ''.join(geohash)

def geohash_decode(geohash: str) -> tuple[float, float]:
    """Decode geohash string to latitude/longitude.

    Returns:
        Tuple of (latitude, longitude) representing the center point of the geohash.
    """
    base32 = '0123456789bcdefghjkmnpqrstuvwxyz'
    lat_interval = (-90.0, 90.0)
    lon_interval = (-180.0, 180.0)
    bits = [16, 8, 4, 2, 1]
    even = True

    for c in geohash:
        idx = base32.index(c)
        for mask in bits:
            if even:
                # Longitude bit
                mid = (lon_interval[0] + lon_interval[1]) / 2
                if idx & mask:
                    lon_interval = (mid, lon_interval[1])
                else:
                    lon_interval = (lon_interval[0], mid)
            else:
                # Latitude bit
                mid = (lat_interval[0] + lat_interval[1]) / 2
                if idx & mask:
                    lat_interval = (mid, lat_interval[1])
                else:
                    lat_interval = (lat_interval[0], mid)
            even = not even

    # Return center point of the geohash box
    latitude = (lat_interval[0] + lat_interval[1]) / 2
    longitude = (lon_interval[0] + lon_interval[1]) / 2
    return latitude, longitude