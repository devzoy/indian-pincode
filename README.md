# Indian Pincode

**Offline-first Indian pincode validation, lookup, and geospatial search — for Python and Node.js.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![Node.js](https://img.shields.io/badge/Node.js-20%2B-green)](https://nodejs.org/)
[![npm](https://img.shields.io/npm/v/%40devzoy%2Findian-pincode)](https://www.npmjs.com/package/@devzoy/indian-pincode)
[![PyPI](https://img.shields.io/pypi/v/indian-pincode)](https://pypi.org/project/indian-pincode/)

Every lookup runs against a dataset embedded directly in the package — no HTTP calls, no
API keys, no rate limits, nothing to go down. The data is India Post's official "All
India Pincode Directory" (via [data.gov.in](https://www.data.gov.in)), cleaned and
compiled into a compact binary format at build time.

v2 splits the library into a small **core** package (validation, state/district lookup)
and an optional **geo** package (post offices, coordinates, nearby search, reverse
lookup) — so applications that only need validation don't pay for geo data they'll never
use. Upgrading from v1? See [MIGRATION.md](MIGRATION.md).

## Table of contents

- [Why embed the data instead of calling an API](#why-embed-the-data-instead-of-calling-an-api)
- [Which package do I need?](#which-package-do-i-need)
- [Install](#install)
- [Quick start](#quick-start)
- [Full API reference](#full-api-reference)
- [Response shape](#response-shape)
- [Accuracy examples](#accuracy-examples)
- [Package size and speed](#package-size-and-speed)
- [Data freshness](#data-freshness)
- [Data quality](#data-quality)
- [License](#license)
- [Contributing](#contributing)
- [FAQ](#faq)

## Why embed the data instead of calling an API

| | This library | A pincode API |
| :--- | :--- | :--- |
| Network calls at runtime | **None** | Every lookup |
| Latency | Sub-millisecond (core), single-digit ms (geo) | Network round-trip, ~100–500 ms typical |
| Availability | Whatever your process's uptime is | Depends on a third party staying up |
| Rate limits | None | Usually yes, past a free tier |
| Data sent off-device | None | Your query (pincode / coordinates) leaves your infra |
| Cost | Free, open source | Often metered past a free tier |
| Freshness | Shipped snapshot, updated on release (see [Data freshness](#data-freshness)) | Provider-managed, may be more current |
| Install size | ~200 KB (core) to ~10 MB (geo, with coordinates for 165k+ post offices) | ~0 |

The honest trade-off is **install size and release-cadence freshness in exchange for
zero runtime dependency on a network call.** If you need always-current data or can't
afford a few hundred KB–10 MB in your bundle, an API-based solution is the better fit —
this library is for the common case where "correct as of last release" is good enough
and you'd rather not add a network dependency to a lookup that should be instant.

## Which package do I need?

| You need… | Install |
| :--- | :--- |
| Validation, pincode → state/district(s), lists | **core** |
| Post offices, coordinates, nearby search, reverse lookup | **geo** (includes core) |

## Install

```bash
# Python
pip install indian-pincode          # core only
pip install "indian-pincode[geo]"   # core + geo

# Node.js
npm install @devzoy/indian-pincode          # core only
npm install @devzoy/indian-pincode-geo      # core + geo (includes core)
```

## Quick start

### Python

```python
import indian_pincode as pincode

pincode.validate("110001")                    # True  (exists in the dataset)
pincode.is_well_formed("999999")               # True  (well-formed 6-digit code, format only)
pincode.get_state("560001")                    # "KARNATAKA"
pincode.get_details("110001")["districts"]     # ["NEW DELHI"]
pincode.list_districts("KERALA")[:3]           # ["ALAPPUZHA", "ERNAKULAM", "IDUKKI"]
```

With the geo extra installed:

```python
import indian_pincode_geo as geo

offices = geo.lookup("110001")
offices[0]["office_name"]                      # "New Delhi GPO"
offices[0]["office_type"]                      # "HO"

nearby = geo.find_nearby(28.6304, 77.2177, radius_km=2)
nearby[0]["office_name"]                       # "Connaught Place SO"
nearby[0]["distance_km"]                       # 0.306

geo.reverse_lookup(28.6304, 77.2177)           # {"pincode": "110001", "distance_km": 0.872}
```

### Node.js

CommonJS shown; ESM works identically (`import pincode from '@devzoy/indian-pincode'`).

```javascript
const pincode = require('@devzoy/indian-pincode');

pincode.validate('110001');                    // true
pincode.isWellFormed('999999');                // true
pincode.getState('560001');                    // "KARNATAKA"
pincode.getDetails('682555').state;             // "LAKSHADWEEP"
pincode.listDistricts('KERALA').slice(0, 3);    // ["ALAPPUZHA", "ERNAKULAM", "IDUKKI"]
```

With the geo package installed:

```javascript
const geo = require('@devzoy/indian-pincode-geo');

geo.lookup('110001')[0].officeName;             // "New Delhi GPO"
geo.lookup('110001')[0].officeType;             // "HO"

const nearby = geo.findNearby(28.6304, 77.2177, { radiusKm: 2 });
nearby[0].officeName;                           // "Connaught Place SO"
nearby[0].distanceKm;                           // 0.306

geo.reverseLookup(28.6304, 77.2177);            // { pincode: "110001", distanceKm: 0.872 }
```

Every call above is **synchronous** in both languages — no `await`, no callbacks.

## Full API reference

### Core (`indian_pincode` / `@devzoy/indian-pincode`)

| Python | Node.js | Returns |
| :--- | :--- | :--- |
| `validate(pin)` | `validate(pin)` | `bool` — pincode exists in the dataset |
| `is_well_formed(pin)` | `isWellFormed(pin)` | `bool` — format check only (6 digits), doesn't imply it exists |
| `get_state(pin)` | `getState(pin)` | primary state name, or `None`/`null` |
| `get_districts(pin)` | `getDistricts(pin)` | list of districts the pincode touches |
| `get_details(pin)` | `getDetails(pin)` | `{pincode, state, states, state_source/stateSource, districts}` |
| `list_states()` | `listStates()` | every state/UT name in the dataset |
| `list_districts(state)` | `listDistricts(state)` | districts that occur **in that state** (scoped, not global) |
| `get_pincodes(state=, district=)` | `getPincodes({state, district})` | pincodes matching the given filter(s) |
| `preload()` | `preload()` | force eager load instead of on first call |
| `DATA_VERSION` | `DATA_VERSION` | dataset snapshot version string |

### Geo (`indian_pincode_geo` / `@devzoy/indian-pincode-geo`)

| Python | Node.js | Returns |
| :--- | :--- | :--- |
| `lookup(pin)` | `lookup(pin)` | list of post offices for that pincode |
| `find_nearby(lat, lon, radius_km=5, limit=20, include_suspect=False)` | `findNearby(lat, lon, {radiusKm, limit, includeSuspect})` | offices within radius, sorted by distance |
| `reverse_lookup(lat, lon)` | `reverseLookup(lat, lon)` | nearest pincode centroid `{pincode, distance_km/distanceKm}` |
| `get_centroid(pin)` | `getCentroid(pin)` | `{latitude, longitude}` for the pincode, or `None`/`null` |

Installing the geo package also gives you the full core API — you don't need to install
both separately.

## Response shape

Field names are **snake_case in Python** and **camelCase in Node** — each idiomatic for
its language. Every geo result carries `geo_quality`/`geoQuality` and
`state_source`/`stateSource` so you can tell how trustworthy a given coordinate or state
assignment is. `find_nearby`/`findNearby` excludes low-quality (`"suspect"`) coordinates
by default; pass `include_suspect=True` / `{ includeSuspect: true }` to include them.
`get_details`/`getDetails` returns the primary `state` (the one with the most post
offices for that pincode; ties broken alphabetically) plus `states` — every state the
pincode actually touches, which is more than one for roughly 52 cross-state pincodes.

## Accuracy examples

Real output from the shipped `2025.10.03` snapshot:

| Query | District | State | Sample offices |
| :--- | :--- | :--- | :--- |
| `110001` | NEW DELHI | DELHI | New Delhi GPO, Connaught Place SO, Parliament House SO |
| `500081` | HYDERABAD | TELANGANA | Madhapur SO, Cyberabad SO |
| `700001` | KOLKATA | WEST BENGAL | Kolkata GPO, Lalbazar SO |
| `560001` | BENGALURU URBAN | KARNATAKA | Bangalore GPO, Bangalore City SO |
| `682555` | ERNAKULAM | LAKSHADWEEP | *(one of ~52 pincodes spanning more than one state — see `states` above)* |

## Package size and speed

Real measured `v2.0.0` numbers (full tables in [docs/BENCHMARKS.md](docs/BENCHMARKS.md)):

| Package | Unpacked |
| :--- | ---: |
| npm core `@devzoy/indian-pincode` | ~208 KB |
| npm geo `@devzoy/indian-pincode-geo` | ~2.7 MB |
| PyPI core `indian-pincode` (wheel data) | ~204 KB |
| PyPI geo `indian-pincode-geo` (SQLite) | ~9.8 MB |

Latency (warm, p50 / p99): `validate` ~0.0005 ms; `find_nearby`/`findNearby` at 5 km
~0.58 / ~1.2 ms (Python), ~0.02 / ~0.10 ms (Node) — both grid-indexed, no full scan over
the dataset.

## Data freshness

- Current snapshot: **`DATA_VERSION` = `2025.10.03`** (the India Post dataset's
  `updated_date` on data.gov.in). Check it at runtime via `DATA_VERSION` /
  `data_version`.
- The dataset is *labelled* monthly on the government portal, but **its content has not
  actually changed since at least October 2025** — the live API feed and a fresh portal
  download are byte-identical to this snapshot.
- Refreshes are therefore **content-gated, not date-gated**: an automated job checks the
  normalized `content_sha256` monthly and only opens a PR when the data genuinely
  changes. Most months it does nothing. Don't assume the data updates every month — it
  updates when India Post actually revises it, and you get it on the next release.

## Data quality

The build pipeline normalizes and cleans the raw dataset; the latest per-build stats are
in [data/REPORT.md](data/REPORT.md). Highlights for `2025.10.03` (19,586 pincodes,
165,625 post offices):

- **Coordinates are approximate.** India Post's lat/long data is imprecise and sometimes
  wrong at the source — this library cleans what it can and flags what it can't.
- Cleaning steps: parse `NA`/junk values to null; validate against India's bounding box;
  detect and fix transposed lat/long pairs (706 rows fixed); flag points that fall far
  from their pincode's coordinate cluster as **`suspect`**.
- **~6.5% of offices (10,686) are flagged `suspect`** and are **excluded from
  `find_nearby`/`findNearby` by default** — pass `include_suspect` / `includeSuspect` to
  include them anyway. ~8.4% of offices have no usable coordinates at all after cleaning.
- State/district names are canonicalized to a single consistent spelling. 715 rows with
  a missing state were backfilled from unambiguous same-pincode or single-state-circle
  evidence (627 successfully backfilled, 88 left `null`), and every backfilled row is
  tagged via `state_source` so you can tell inferred data from source data.

## License

- **Code:** MIT — see [LICENSE](LICENSE).
- **Data:** derived from India Post / data.gov.in under the Government Open Data License
  – India (GODL-India), which requires attribution. See [DATA_LICENSE.md](DATA_LICENSE.md)
  for the required attribution text.

## Contributing

Bug reports, data corrections, and PRs are welcome.

- **Found incorrect data?** Open an issue with the pincode and what's wrong — the
  underlying dataset comes from India Post, but if it's something the cleaning pipeline
  should catch (a bad coordinate, a malformed name), it's a pipeline bug, not just a data
  gap.
- **Want to run the pipeline locally?** `python -m pipeline.build` regenerates all
  package data from the canonical dataset — see [pipeline/README.md](pipeline/README.md).
- **Publishing / release process:** see [PUBLISHING.md](PUBLISHING.md) if you're a
  maintainer cutting a release.

## FAQ

**Why not just call an API?** See [Why embed the data instead of calling an API](#why-embed-the-data-instead-of-calling-an-api)
above — it's a real trade-off, not a strictly-better choice either way.

**Can I use core without geo, or vice versa?** Core works standalone. Geo depends on
core and re-exports its functions, so installing geo alone gives you everything.

**Why are Node's field names camelCase but Python's are snake_case?** Each matches the
idiomatic convention for its language rather than forcing one convention on both.

**Is the data authoritative / official?** It's derived from India Post's own published
dataset, cleaned by this project's pipeline. For anything safety- or compliance-critical,
verify against the source before relying on it.

**How often is the data updated?** See [Data freshness](#data-freshness) — content-gated,
not calendar-gated.
