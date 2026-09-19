# @devzoy/indian-pincode-geo

**Post offices, coordinates, nearby search, and reverse lookup for Indian pincodes —
offline, no runtime network calls.**

[![npm](https://img.shields.io/npm/v/%40devzoy%2Findian-pincode-geo)](https://www.npmjs.com/package/@devzoy/indian-pincode-geo)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Companion package to [`@devzoy/indian-pincode`](https://www.npmjs.com/package/@devzoy/indian-pincode)
(core). Installing this package gives you the **full core API plus geo functions** — you
don't need to install both separately. **Node-only** (reads its data file from disk
lazily); not intended for browser bundles — use core alone there.

## Install

```bash
npm install @devzoy/indian-pincode-geo
```

## Usage

CommonJS shown; ESM works identically (`import geo from '@devzoy/indian-pincode-geo'`).

```js
const geo = require('@devzoy/indian-pincode-geo');

// Core functions are available too — no need to also install the core package
geo.validate('110001');                          // true

// Post offices for a pincode
const offices = geo.lookup('110001');
offices[0].officeName;                            // "New Delhi GPO"
offices[0].officeType;                             // "HO"
offices[0].geoQuality;                             // "original"

// Nearby search
const nearby = geo.findNearby(28.6304, 77.2177, { radiusKm: 2 });
nearby[0].officeName;                              // "Connaught Place SO"
nearby[0].distanceKm;                              // 0.306

// Reverse geocode to nearest pincode
geo.reverseLookup(28.6304, 77.2177);               // { pincode: "110001", distanceKm: 0.872 }

// Centroid of a pincode
geo.getCentroid('110001');                         // { latitude: 28.62273, longitude: 77.21954 }
```

## API reference

| Function | Returns |
| :--- | :--- |
| `lookup(pin)` | array of post offices for that pincode |
| `findNearby(lat, lon, { radiusKm = 5, limit = 20, includeSuspect = false })` | offices within radius, sorted by distance, each with `distanceKm` |
| `reverseLookup(lat, lon)` | nearest pincode centroid: `{ pincode, distanceKm }` |
| `getCentroid(pin)` | `{ latitude, longitude }` for the pincode, or `null` |

Plus the entire [core API](https://www.npmjs.com/package/@devzoy/indian-pincode#api-reference)
(`validate`, `getDetails`, `listDistricts`, etc.) — re-exported so you only need this one
package.

Every office/result carries `geoQuality` (`"original"`, `"swapped"`, or `"suspect"`) and
`stateSource`. `findNearby` and `reverseLookup` **exclude `"suspect"` coordinates by
default** — pass `includeSuspect: true` to include them anyway. See
[Data quality](#data-quality) for what that means and how common it is.

## Requirements

Node **>=20**.

## Data quality

India Post's coordinates are approximate, and occasionally wrong at the source — lat/lon
swapped, or simply implausible. The build pipeline validates every coordinate against
India's bounding box, auto-corrects detected lat/lon swaps, and flags points that fall
far from their pincode's coordinate cluster as `geoQuality: "suspect"`.

- **~6.5% of offices (10,686)** are flagged `suspect` and excluded from `findNearby`/
  `reverseLookup` by default.
- **~8.4% of offices** have no usable coordinates at all after cleaning (`latitude`/
  `longitude` are `null`).
- Full methodology and per-build stats: [data/REPORT.md](https://github.com/devzoy/indian-pincode/blob/main/data/REPORT.md).

If your use case needs every point regardless of confidence (e.g. you're doing your own
outlier analysis), pass `includeSuspect: true` — don't assume the default is "all data."

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
- [Core package](https://www.npmjs.com/package/@devzoy/indian-pincode) (if you only need validation, no geo data)
- [v1 → v2 migration guide](https://github.com/devzoy/indian-pincode/blob/main/MIGRATION.md)
- [Report a data issue](https://github.com/devzoy/indian-pincode/issues)
