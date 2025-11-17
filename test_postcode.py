"""Test script for postcode lookup functionality.

Run this to test postcode lookups without Home Assistant:
    python test_postcode.py
"""
import asyncio

try:
    import pgeocode
    print("✓ pgeocode library is available")
    PGEOCODE_AVAILABLE = True
except ImportError:
    print("✗ pgeocode library not installed. Install with: pip install pgeocode")
    PGEOCODE_AVAILABLE = False
    exit(1)


def test_postcode(postcode):
    """Test postcode lookup."""
    print(f"\nTesting postcode: {postcode}")
    nomi = pgeocode.Nominatim('AU')
    location = nomi.query_postal_code(postcode)

    if location.latitude is None or location.longitude is None:
        print(f"  ✗ Invalid postcode: {postcode}")
        return None
    else:
        print(f"  ✓ Latitude: {location.latitude}")
        print(f"  ✓ Longitude: {location.longitude}")
        print(f"  ✓ Place name: {location.place_name}")
        print(f"  ✓ State: {location.state_code}")
        return (location.latitude, location.longitude)


async def test_with_collector(postcode):
    """Test with actual BOM collector."""
    print(f"\nTesting BOM data fetch for postcode: {postcode}")

    # Get coordinates from postcode
    coords = test_postcode(postcode)
    if not coords:
        return

    # Import collector
    import sys
    sys.path.insert(0, '/home/user/ha_bom_australia/custom_components/ha_bom_australia')
    from PyBoM.collector import Collector

    # Create collector and fetch data
    collector = Collector(coords[0], coords[1])
    await collector.get_locations_data()

    if collector.locations_data:
        print(f"\n✓ Successfully fetched BOM location data:")
        print(f"  Location: {collector.locations_data['data']['name']}")
        print(f"  Geohash: {collector.geohash7}")

        # Fetch full data
        await collector.async_update()

        if collector.observations_data:
            obs = collector.observations_data['data']
            print(f"\n✓ Observation data:")
            print(f"  Station: {obs.get('station', {}).get('name')}")
            print(f"  Temperature: {obs.get('temp')}°C")
            print(f"  Humidity: {obs.get('humidity')}%")
    else:
        print("✗ Failed to fetch BOM data")


if __name__ == "__main__":
    # Test common Australian postcodes
    test_postcodes = [
        "3000",  # Melbourne CBD
        "2000",  # Sydney CBD
        "4000",  # Brisbane CBD
        "6000",  # Perth CBD
        "5000",  # Adelaide CBD
        "7000",  # Hobart CBD
        "0800",  # Darwin
        "2600",  # Canberra
    ]

    print("=" * 60)
    print("Testing Postcode Lookup Functionality")
    print("=" * 60)

    for postcode in test_postcodes:
        test_postcode(postcode)

    # Test with actual BOM collector for one location
    print("\n" + "=" * 60)
    print("Testing BOM API Integration")
    print("=" * 60)

    asyncio.run(test_with_collector("3000"))

    print("\n" + "=" * 60)
    print("All tests complete!")
    print("=" * 60)
