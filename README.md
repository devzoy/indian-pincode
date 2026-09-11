# Indian Pincode

**Offline-first Indian pincode validation, lookup, and geospatial search for Python and Node.js.**

<!-- [![CI](https://github.com/devzoy/indian-pincode/workflows/CI/badge.svg)](https://github.com/devzoy/indian-pincode/actions) -->
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![Node.js](https://img.shields.io/badge/Node.js-20%2B-green)](https://nodejs.org/)

Lookups run against an embedded dataset (sourced from the India Post "All India Pincode
Directory" on [data.gov.in](https://www.data.gov.in)), so there are **no network calls at
runtime**. v2 splits into a small **core** (validation + state/district) and an optional
**geo** package (post offices, coordinates, nearby search). See
[MIGRATION.md](MIGRATION.md) for v1 → v2.

## Which package do I need?

| You need… | Install |
| :--- | :--- |
| Validation, pincode → state/district(s), lists | **core** |
| Post offices, coordinates, nearby search, reverse lookup | **geo** (includes core) |

## Install

```bash
# Python
pip install indian-pincode          # core
pip install "indian-pincode[geo]"   # core + geo

# Node.js
npm install @devzoy/indian-pincode          # core
npm install @devzoy/indian-pincode-geo      # core + geo
```

## Quick start — Python

```python
import indian_pincode as pincode

print(pincode.validate("110001"))            # True
print(pincode.is_well_formed("999999"))      # True
print(pincode.get_state("560001"))           # KARNATAKA
print(pincode.get_details("110001")["districts"])  # ['NEW DELHI']
```

With the geo extra installed:

```python
import indian_pincode_geo as geo

offices = geo.lookup("110001")
print(offices[0]["office_name"])             # New Delhi GPO
print(offices[0]["office_type"])             # HO
nearby = geo.find_nearby(28.6304, 77.2177, radius_km=2)
print(nearby[0]["office_name"])              # Connaught Place SO
```

## Quick start — Node.js

CommonJS (ESM: `import pincode from '@devzoy/indian-pincode'`):

```javascript
const pincode = require('@devzoy/indian-pincode');

console.log(pincode.validate('110001'));             // => true
console.log(pincode.isWellFormed('999999'));         // => true
console.log(pincode.getState('560001'));             // => KARNATAKA
console.log(pincode.getDetails('682555').state);     // => LAKSHADWEEP
```

With the geo package installed:

```javascript
const geo = require('@devzoy/indian-pincode-geo');

console.log(geo.lookup('110001')[0].officeName);     // => New Delhi GPO
console.log(geo.lookup('110001')[0].officeType);     // => HO
console.log(geo.findNearby(28.6304, 77.2177, { radiusKm: 2 })[0].officeName); // => Connaught Place SO
```

## Response shape

Field names are **snake_case in Python** and **camelCase in Node**. Every geo result
carries `geo_quality`/`geoQuality` and `state_source`/`stateSource`. `find_nearby`/
`findNearby` excludes low-quality ("suspect") coordinates by default; pass
`include_suspect=True` / `{ includeSuspect: true }` to include them. `get_details`/
`getDetails` returns the primary `state` (most post offices; ties alphabetical) plus
`states` (all states the pincode touches).

## Package sizes

Real measured `v2.0.0` sizes (see [docs/BENCHMARKS.md](docs/BENCHMARKS.md)):

| Package | Unpacked |
| :--- | ---: |
| npm core `@devzoy/indian-pincode` | ~213 KB |
| npm geo `@devzoy/indian-pincode-geo` | ~2.8 MB |
| PyPI core `indian-pincode` | ~260 KB |
| PyPI geo `indian-pincode-geo` | ~9.8 MB |

## Data

- Snapshot version is exposed as `DATA_VERSION` / `data_version` (`YYYY.MM.DD`).
- Cleaning rules and per-build stats: [data/REPORT.md](data/REPORT.md). India Post
  coordinates are approximate; low-quality points are flagged and excluded from geo
  search by default.

## Library vs. self-hosting vs. an API

The trade-off is **data freshness and package size** vs. runtime independence — not just
latency. If you need always-current data or a tiny install, an API or self-hosting the raw
dataset may fit better. If you want offline, dependency-free lookups on a release cadence,
this library fits well.

## License

- **Code:** MIT — see [LICENSE](LICENSE).
- **Data:** derived from India Post / data.gov.in under the Government Open Data License –
  India (GODL-India), which requires attribution. See [DATA_LICENSE.md](DATA_LICENSE.md).

## Contributing

Run the pipeline locally with `python -m pipeline.build` (see [pipeline/README.md](pipeline/README.md)).
To report a data error, open an issue with the pincode and the expected value.
