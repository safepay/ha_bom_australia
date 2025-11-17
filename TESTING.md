# Testing Guide for BOM Australia Integration

## Testing Postcode Lookup Feature

The postcode lookup feature allows users to enter an Australian postcode instead of latitude/longitude coordinates when setting up the integration.

### Manual Testing in Home Assistant

1. **Install the integration** in your Home Assistant instance (via HACS custom repository or manually)
2. **Go to** Settings → Devices & Services → Add Integration
3. **Search for** "BOM Australia"
4. **Test postcode entry**:
   - Leave latitude and longitude blank (or at default values)
   - Enter an Australian postcode (e.g., 3000, 2000, 4000)
   - Click Submit
   - The integration should resolve the postcode to coordinates and find the nearest BOM station

### Common Test Postcodes

| City | Postcode | Expected Location |
|------|----------|-------------------|
| Melbourne CBD | 3000 | Melbourne |
| Sydney CBD | 2000 | Sydney |
| Brisbane CBD | 4000 | Brisbane |
| Perth CBD | 6000 | Perth |
| Adelaide CBD | 5000 | Adelaide |
| Hobart CBD | 7000 | Hobart |
| Darwin | 0800 | Darwin |
| Canberra | 2600 | Canberra |

### Testing Multiple Locations

The postcode feature makes it easy to set up multiple locations:

1. Add first location using postcode (e.g., 3000 for Melbourne)
2. Add second location using a different postcode (e.g., 2000 for Sydney)
3. Each will get its own entity prefix and sensors

### Error Testing

Test that the integration handles errors correctly:

1. **Invalid postcode**: Enter "9999" → Should show error message
2. **Empty fields**: Leave all fields blank → Should show "Please provide either latitude/longitude OR a postcode"
3. **Partial coordinates**: Enter only latitude → Should show error
4. **Postcode override**: Enter both coordinates AND postcode → Postcode should take precedence

### Fallback Testing

If `pgeocode` is not available or fails:

1. Integration should fall back to requiring latitude/longitude
2. Should show standard coordinate input fields
3. Should not crash or show errors about missing pgeocode

## Testing Without Home Assistant

You can test the postcode lookup functionality without a full Home Assistant installation:

### Option 1: Using the test script

```bash
cd /home/user/ha_bom_australia
python test_postcode.py
```

This will:
- Test postcode lookup for major Australian cities
- Verify coordinates are returned correctly
- Test BOM API integration with resolved coordinates

### Option 2: Python REPL Testing

```python
import pgeocode

# Initialize for Australia
nomi = pgeocode.Nominatim('AU')

# Test a postcode
location = nomi.query_postal_code('3000')

print(f"Latitude: {location.latitude}")
print(f"Longitude: {location.longitude}")
print(f"Place: {location.place_name}")
print(f"State: {location.state_code}")
```

## Automated Testing

### Unit Tests (Future)

Create unit tests in `tests/test_config_flow.py`:

```python
async def test_postcode_lookup(hass):
    """Test postcode lookup in config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"postcode": "3000"}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "weather_name"
```

### Integration Tests

Test the full flow:

1. Postcode → Coordinates conversion
2. Coordinates → BOM station lookup
3. Station → Data fetch
4. Entity creation

## Troubleshooting Tests

### pgeocode Database Issues

If you see "HTTP Error 403" when testing:

- This is a known issue with GeoNames.org rate limiting
- Wait a few minutes and try again
- Or use latitude/longitude as fallback

### Network Issues

The postcode feature requires:
- Internet access to download AU postcode database (first time only)
- Internet access to reach BOM API

Test offline behavior:
- Disable network
- Attempt postcode lookup
- Should fail gracefully with error message
- Should allow fallback to lat/long

## Verification Checklist

- [ ] Postcode 3000 resolves to Melbourne coordinates
- [ ] Invalid postcode shows error message
- [ ] Empty fields show appropriate error
- [ ] Postcode overrides lat/long when both provided
- [ ] Multiple locations can be added via postcode
- [ ] Fallback to lat/long works when postcode fails
- [ ] Entity prefix is applied correctly regardless of input method
- [ ] BOM station lookup succeeds with postcode-derived coordinates

## Known Limitations

1. **First-time setup**: Requires download of ~2MB AU postcode database from GeoNames.org
2. **Network dependency**: Postcode lookup requires internet access
3. **Accuracy**: Postcodes resolve to approximate center of postcode area, not exact location
4. **Coverage**: Only Australian postcodes are supported

## Support

If postcode lookup isn't working:

1. Check Home Assistant logs for errors
2. Try using latitude/longitude instead
3. Verify `pgeocode` is installed: `pip show pgeocode`
4. Report issues at: https://github.com/safepay/ha_bom_australia/issues
