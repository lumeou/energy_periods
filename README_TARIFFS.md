# Tariffs Configuration (Phase 2.1)

This document explains how to configure dynamic tariffs using JSON files with date-based ranges.

## Overview

The Energy Periods integration now supports **tariff configurations with date ranges**, allowing you to:

- Define different periods and prices for different time periods
- Plan price changes in advance
- Manage tariff evolution over time
- Use a single JSON file for all your tariff configurations

## File Format

### New Format: With Date Ranges

```json
{
  "tariffs": [
    {
      "from_date": "2024-01-01",
      "to_date": "2024-12-31",
      "periods": { ... },
      "prices": { ... }
    },
    {
      "from_date": "2025-01-01",
      "to_date": null,
      "periods": { ... },
      "prices": { ... }
    }
  ]
}
```

**Key points:**
- `from_date`: When this tariff becomes active (format: `YYYY-MM-DD`)
- `to_date`: When this tariff expires (format: `YYYY-MM-DD` or `null` for open-ended)
- `periods`: Time-based periods definition (working_day, non_working_day, fallback)
- `prices`: Price mappings for each period type

### Legacy Format (Auto-converted)

If you have an existing configuration file in the old format:

```json
{
  "periods": { ... },
  "prices": { ... }
}
```

The integration will **automatically convert** it to the new format (single tariff with open-ended range).

## Configuration Examples

### Example 1: Single Tariff (Legacy equivalent)

```json
{
  "tariffs": [
    {
      "from_date": null,
      "to_date": null,
      "periods": {
        "working_day": [
          {"start": "00:00", "end": "08:00", "type": "valle"},
          {"start": "08:00", "end": "22:00", "type": "punta"},
          {"start": "22:00", "end": "00:00", "type": "llano"}
        ],
        "non_working_day": [
          {"start": "00:00", "end": "00:00", "type": "valle"}
        ],
        "fallback": {"type": "valle"}
      },
      "prices": {
        "valle": 0.082334,
        "llano": 0.116414,
        "punta": 0.185461
      }
    }
  ]
}
```

### Example 2: Multiple Tariffs with Date Ranges

See `TARIFFS_EXAMPLE.json` for a complete example with:
- 2024 pricing
- 2025 pricing (different rates)
- Automatic switching on Jan 1, 2025

## How to Use

1. **Prepare your JSON file**
   - Copy `TARIFFS_EXAMPLE.json` as a starting point
   - Modify periods and prices as needed
   - Ensure valid JSON syntax

2. **Import in Home Assistant**
   - Open Energy Periods integration options
   - Click "📋 Tariffs (JSON file)"
   - Upload your JSON file
   - Confirm and save

3. **Verification**
   - The integration will validate the configuration
   - Error messages will indicate what's wrong (if any)
   - Once saved, it takes effect immediately

## Validation Rules

The JSON is validated for:

- ✅ Valid JSON syntax
- ✅ Required fields: `tariffs`, `periods`, `prices`
- ✅ Tariff dates format (YYYY-MM-DD or null)
- ✅ Period time format (HH:MM)
- ✅ No overlapping periods within a day type
- ✅ Price values are positive numbers

## Date Range Logic

### How tariffs are selected

For any given date, the integration finds the **first tariff** where:
- `from_date` is `null` OR date >= `from_date`
- AND `to_date` is `null` OR date <= `to_date`

### Examples

```
from_date: "2024-01-01", to_date: "2024-12-31"
→ Active from Jan 1, 2024 through Dec 31, 2024

from_date: "2025-01-01", to_date: null
→ Active from Jan 1, 2025 onwards (no end date)

from_date: null, to_date: null
→ Always active (default)
```

### Overlapping dates (unusual case)

If tariffs overlap:
```
Tariff A: 2024-01-01 to 2024-12-31
Tariff B: 2024-06-01 to 2025-12-31
```

On June 15, 2024: **Tariff A is used** (first match in array order)

**Recommendation:** Avoid overlaps or use non-overlapping ranges.

## Future Features (Phase 2.2+)

- YAML format support in `configuration.yaml`
- Import/export from UI
- Visual date range editor
- Tariff templates library

## Troubleshooting

### "Invalid JSON format"
- Check JSON syntax (use a JSON validator)
- Ensure proper quotes and commas

### "Invalid configuration structure"
- Missing `tariffs` key (for new format)
- Missing `periods` or `prices` keys
- `tariffs` is empty array

### "Periods cannot overlap"
- Check time ranges in each tariff's periods
- Example issue: `"08:00" → "10:00"` overlaps with `"10:00" → "12:00"` (should be `"08:00" → "10:00"` and `"10:00" → "12:00"`)

### Price not applied
- Verify period type name matches between periods and prices
- Check date ranges with `from_date` and `to_date`

## Period Types Guide

Period types are customizable (common examples):

- **valle** (valley): Low cost period
- **punta** (peak): High cost period
- **llano** (flat): Medium cost period
- Custom names allowed (must be defined in both periods and prices)

## Notes

- Tariff changes take effect immediately (no service restart needed)
- Backfill service respects the tariff valid at each historical date
- Configuration is validated before being saved
