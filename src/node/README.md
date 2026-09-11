# Indian Pincode — Node.js

[![npm version](https://img.shields.io/npm/v/@devzoy/indian-pincode.svg)](https://www.npmjs.com/package/@devzoy/indian-pincode)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Node.js](https://img.shields.io/badge/Node.js-18%2B-green)](https://nodejs.org/)

**Offline-first Indian pincode validation, lookup, and geospatial search for Node.js.**

Lookups run against an embedded dataset (sourced from the India Post "All India Pincode
Directory" on [data.gov.in](https://www.data.gov.in)), so there are **no network calls at
runtime**.

## Library vs. an API

The trade-off is **data freshness and package size** vs. runtime independence.

| Consideration | External API | This library |
| :--- | :--- | :--- |
| Runtime network calls | Required | None (all local) |
| Availability / rate limits | Subject to provider | Not applicable at runtime |
| Data freshness | Provider-managed | Fixed to the shipped snapshot; update by upgrading |
| Install size | Tiny client | Larger (embedded dataset) |
| Lookup latency | Network round-trip | Local (sub-ms validation; single-digit ms geo search) |

## Installation

```bash
npm install @devzoy/indian-pincode
# or
yarn add @devzoy/indian-pincode
```

## Usage

### CommonJS

```javascript
const pincode = require('@devzoy/indian-pincode');

// Validate (true only if the pincode exists in the dataset)
pincode.validate("110001");  // true
pincode.validate("999999");  // false

// Lookup (returns a Promise in v1.x)
pincode.lookup("110001").then(offices => {
    const o = offices[0];
    console.log(o.office);     // post office name
    console.log(o.district);   // e.g. "NEW DELHI"
    console.log(o.state);      // "DELHI"
    console.log(o.latitude);   // latitude (string in v1.x)
    console.log(o.longitude);  // longitude (string in v1.x)
});

// Find nearby post offices within a radius (km) of a coordinate
pincode.findNearby(28.63, 77.21, 5).then(results => {
    results.forEach(o => {
        console.log(`${o.pincode} - ${o.office} (${o.distance} km)`);
    });
});

// Search all offices in a district (case-insensitive substring match)
pincode.searchByDistrict("BENGALURU").then(results => {
    console.log(`Found ${results.length} office rows`);
});
```

### ESM

```javascript
import pincode from '@devzoy/indian-pincode';

const offices = await pincode.lookup("110001");
console.log(offices[0].office);
```

> **v1.x note:** `lookup`, `findNearby`, and `searchByDistrict` return Promises. Result
> order is not guaranteed — do not rely on `offices[0]` being a specific office. v2 makes
> these synchronous and sorts results deterministically. See
> [MIGRATION.md](../../MIGRATION.md) once v2 lands.

## API Reference

### `validate(pincode)`
Returns `boolean`. `true` only if the pincode exists in the dataset (not merely if it is
six digits).

### `lookup(pincode)`
Returns `Promise<Array>` of office objects: `pincode`, `office`, `district`, `state`,
`latitude`, `longitude`.

### `findNearby(latitude, longitude, radiusKm = 5)`
Returns `Promise<Array>` of offices within the radius, sorted by distance. Each item
includes `pincode` and a numeric `distance` (km) field.

### `searchByDistrict(districtName)`
Returns `Promise<Array>` of office rows whose district matches (case-insensitive
substring). `searchDistricts(query)` returns matching district **names** (synchronous).

## Technical details

- Pure JavaScript, no runtime dependencies.
- Validation index and per-prefix detail chunks are loaded lazily via `fs`.
- Distances use the haversine formula.

> **v1.x limitation:** `findNearby` scans all pincode-level points on each call and reads
> detail chunks per match; it is correct but not optimized. v2 adds a spatial index.

## License

- **Code:** MIT — see [LICENSE](../../LICENSE).
- **Data:** GODL-India (attribution required) — see [DATA_LICENSE.md](../../DATA_LICENSE.md).

## Links

- Python package: `pip install indian-pincode`
- Repository: [github.com/devzoy/indian-pincode](https://github.com/devzoy/indian-pincode)
- Issues: [GitHub Issues](https://github.com/devzoy/indian-pincode/issues)
