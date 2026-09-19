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

## Package sizes and speed

Real measured `v2.0.0` numbers (full tables in [docs/BENCHMARKS.md](docs/BENCHMARKS.md)):

| Package | Unpacked |
| :--- | ---: |
| npm core `@devzoy/indian-pincode` | ~208 KB |
| npm geo `@devzoy/indian-pincode-geo` | ~2.7 MB |
| PyPI core `indian-pincode` (wheel data) | ~204 KB |
| PyPI geo `indian-pincode-geo` (SQLite) | ~9.8 MB |

Latency (warm, p50 / p99): `validate` ~0.0005 ms; `find_nearby`/`findNearby` at 5 km
~0.58 / ~1.2 ms (Python), ~0.02 / ~0.10 ms (Node) — grid-indexed, no full scan.

## Data freshness

- Current snapshot: **`DATA_VERSION` = `2025.10.03`** (from the India Post dataset's
  `updated_date` on data.gov.in). Check it at runtime via `DATA_VERSION` /
  `data_version`.
- The dataset is *labelled* monthly, but **its content has not actually changed since at
  least October 2025** — the API feed and a fresh portal download are byte-identical to
  the earlier snapshot.
- Refreshes are therefore **content-gated, not date-gated**: an automated job checks the
  normalized `content_sha256` monthly and only opens a PR when the data genuinely
  changes. Most months it does nothing. So do not assume the data updates monthly — it
  updates when India Post actually revises it, and you get it on the next release.

## Data quality

The build pipeline normalizes and cleans the raw dataset; the latest per-build stats are
in [data/REPORT.md](data/REPORT.md). Highlights for `2025.10.03` (19,586 pincodes,
165,625 post offices):

- **Coordinates are approximate.** India Post lat/long are imprecise and sometimes wrong.
- Cleaning: parse `NA`/junk → null; validate against India's bounding box; swap
  transposed lat/long (706 fixed); flag points far from their pincode's cluster as
  **`suspect`**.
- **~6.5% of offices (10,686) are flagged `suspect`** and are **excluded from
  `find_nearby`/`findNearby` by default** (pass `include_suspect` / `includeSuspect` to
  include them). ~8.4% of offices have no usable coordinates after cleaning.
- State/district names are canonicalized; 715 rows with a missing state were backfilled
  from unambiguous same-pincode or single-state-circle evidence (627 backfilled, 88 left
  null), each tagged with `state_source`.

## When to use this vs. self-hosting vs. an API

| | This library | Self-host the raw CSV | An API |
| :--- | :--- | :--- | :--- |
| Runtime network | none | none | required |
| Freshness | shipped snapshot, updated on release | whatever you fetch | provider-managed |
| Install / infra | one dependency | you build the query layer | a client + a key |
| Latency | sub-ms (core), single-digit ms (geo) | your call | network round-trip |
| Best when | offline, dependency-free, release-cadence updates are fine | you want the raw data and your own schema | you need always-current data or minimal install |

The honest trade-off is **freshness and package size vs. runtime independence** — not
just latency.

## License

- **Code:** MIT — see [LICENSE](LICENSE).
- **Data:** derived from India Post / data.gov.in under the Government Open Data License –
  India (GODL-India), which requires attribution. See [DATA_LICENSE.md](DATA_LICENSE.md).

## Contributing

Run the pipeline locally with `python -m pipeline.build` (see [pipeline/README.md](pipeline/README.md)).
To report a data error, open an issue with the pincode and the expected value.
