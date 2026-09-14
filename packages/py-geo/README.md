# indian-pincode-geo

Geo companion for `indian-pincode`: **post offices, coordinates, nearby search, and
reverse lookup**. Offline, no runtime network calls. Depends on `indian-pincode` (exact
same version). Importing it also enables `indian_pincode.lookup(...)` etc.

Requires Python **>=3.10**. Install via the core extra: `pip install "indian-pincode[geo]"`.

## Usage

```python
import indian_pincode_geo as geo

offices = geo.lookup("110001")
print(offices[0]["office_name"])              # New Delhi GPO
print(offices[0]["office_type"])              # HO
nearby = geo.find_nearby(28.6304, 77.2177, radius_km=2)
print(nearby[0]["office_name"])               # Connaught Place SO
```

- Result keys are **snake_case**: `pincode, office_name, office_type, delivery_status,
  district, state, state_source, latitude, longitude, geo_quality` (and `distance_km`
  from `find_nearby`).
- `find_nearby(lat, lon, radius_km=5, limit=20, include_suspect=False)` returns offices
  sorted by distance. `reverse_lookup(lat, lon)` returns the nearest pincode centroid
  `{pincode, distance_km}`. `get_centroid(pin)` returns `{latitude, longitude}`.

## Data quality

India Post coordinates are **approximate**. The pipeline flags points that are far from
their pincode's cluster as `geo_quality == "suspect"` — about **6.5%** of offices — and
`find_nearby`/`reverse_lookup` **exclude them by default**. Pass `include_suspect=True` to
include them. About 8.4% of offices have no usable coordinates after cleaning. Full stats:
[data/REPORT.md](https://github.com/devzoy/indian-pincode/blob/main/data/REPORT.md).

## License

- **Code:** MIT.
- **Data:** derived from India Post / data.gov.in under GODL-India (attribution
  required) — see [DATA_LICENSE.md](DATA_LICENSE.md).
