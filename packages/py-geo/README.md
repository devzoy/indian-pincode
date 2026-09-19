# indian-pincode-geo

**Post offices, coordinates, nearby search, and reverse lookup for Indian pincodes —
offline, no runtime network calls.**

[![PyPI](https://img.shields.io/pypi/v/indian-pincode-geo)](https://pypi.org/project/indian-pincode-geo/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Companion package to [`indian-pincode`](https://pypi.org/project/indian-pincode/) (core),
pinned to the **exact same version**. Install via the core package's geo extra:

```bash
pip install "indian-pincode[geo]"
```

Importing `indian_pincode_geo` also patches `indian_pincode` so its top-level functions
(`indian_pincode.lookup(...)`, etc.) work — you don't need to juggle two import
statements.

## Usage

```python
import indian_pincode_geo as geo

# Post offices for a pincode
offices = geo.lookup("110001")
offices[0]["office_name"]                        # "New Delhi GPO"
offices[0]["office_type"]                         # "HO"
offices[0]["geo_quality"]                         # "original"

# Nearby search
nearby = geo.find_nearby(28.6304, 77.2177, radius_km=2)
nearby[0]["office_name"]                          # "Connaught Place SO"
nearby[0]["distance_km"]                          # 0.306

# Reverse geocode to nearest pincode
geo.reverse_lookup(28.6304, 77.2177)              # {"pincode": "110001", "distance_km": 0.872}

# Centroid of a pincode
geo.get_centroid("110001")                        # {"latitude": 28.62273, "longitude": 77.21954}
```

## API reference

| Function | Returns |
| :--- | :--- |
| `lookup(pin)` | list of post offices for that pincode |
| `find_nearby(lat, lon, radius_km=5, limit=20, include_suspect=False)` | offices within radius, sorted by distance, each with `distance_km` |
| `reverse_lookup(lat, lon)` | nearest pincode centroid: `{pincode, distance_km}` |
| `get_centroid(pin)` | `{latitude, longitude}` for the pincode, or `None` |

Plus the entire [core API](https://pypi.org/project/indian-pincode/#api-reference)
(`validate`, `get_details`, `list_districts`, etc.), available directly from
`indian_pincode` once this package is imported.

Result keys are **snake_case**: `pincode, office_name, office_type, delivery_status,
district, state, state_source, latitude, longitude, geo_quality` (plus `distance_km` on
`find_nearby`/`reverse_lookup` results). Every result carries `geo_quality`
(`"original"`, `"swapped"`, or `"suspect"`) and `state_source`. `find_nearby` and
`reverse_lookup` **exclude `"suspect"` coordinates by default** — pass
`include_suspect=True` to include them anyway. See [Data quality](#data-quality) for
what that means and how common it is.

## Requirements

Python **>=3.10**.

## Data quality

India Post's coordinates are approximate, and occasionally wrong at the source — lat/lon
swapped, or simply implausible. The build pipeline validates every coordinate against
India's bounding box, auto-corrects detected lat/lon swaps, and flags points that fall
far from their pincode's coordinate cluster as `geo_quality == "suspect"`.

- **~6.5% of offices (10,686)** are flagged `suspect` and excluded from `find_nearby`/
  `reverse_lookup` by default.
- **~8.4% of offices** have no usable coordinates at all after cleaning (`latitude`/
  `longitude` are `None`).
- Full methodology and per-build stats: [data/REPORT.md](https://github.com/devzoy/indian-pincode/blob/main/data/REPORT.md).

If your use case needs every point regardless of confidence (e.g. you're doing your own
outlier analysis), pass `include_suspect=True` — don't assume the default is "all data."

## Data freshness

`DATA_VERSION` is the India Post snapshot date this build was compiled from (currently
`2025.10.03`). Releases are content-gated: you get new data when India Post actually
revises the source, not on a fixed monthly schedule.

## License

- **Code:** MIT.
- **Data:** derived from India Post / data.gov.in under the Government Open Data License
  – India (GODL-India), which requires attribution — see [DATA_LICENSE.md](DATA_LICENSE.md).

## Links

- [Full project README](https://github.com/devzoy/indian-pincode) (both languages, both packages, benchmarks, FAQ)
- [Core package](https://pypi.org/project/indian-pincode/) (if you only need validation, no geo data)
- [v1 → v2 migration guide](https://github.com/devzoy/indian-pincode/blob/main/MIGRATION.md)
- [Report a data issue](https://github.com/devzoy/indian-pincode/issues)
