# @devzoy/indian-pincode (core)

**Offline-first Indian pincode validation and pincode → state/district lookup for
Node.js, browsers, and edge runtimes.**

[![npm](https://img.shields.io/npm/v/%40devzoy%2Findian-pincode)](https://www.npmjs.com/package/@devzoy/indian-pincode)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

No runtime network calls, no Node built-ins in the bundle — this package works
identically in Node, browsers, bundlers (Vite/webpack/esbuild), edge runtimes (Workers,
Deno Deploy), and React Native. For post offices, coordinates, and geospatial search,
install the companion [`@devzoy/indian-pincode-geo`](https://www.npmjs.com/package/@devzoy/indian-pincode-geo)
package — it re-exports everything here plus geo functions, so you only need one import.

## Install

```bash
npm install @devzoy/indian-pincode
```

## Usage

CommonJS shown; ESM works identically (`import pincode from '@devzoy/indian-pincode'`).

```js
const pincode = require('@devzoy/indian-pincode');

pincode.validate('110001');                     // true  — exists in the dataset
pincode.isWellFormed('999999');                  // true  — well-formed 6-digit code, format only
pincode.getState('560001');                      // "KARNATAKA"
pincode.getDetails('682555').state;              // "LAKSHADWEEP"
pincode.getDistricts('110025');                  // ["BUDAUN", "SOUTH", "SOUTH EAST"] — cross-state pincode
pincode.listStates().length;                     // 36
pincode.listDistricts('KERALA').slice(0, 3);     // ["ALAPPUZHA", "ERNAKULAM", "IDUKKI"]
pincode.getPincodes({ state: 'GOA' }).length;     // pincodes in Goa
```

## API reference

| Function | Returns |
| :--- | :--- |
| `validate(pin)` | `boolean` — pincode exists in the dataset |
| `isWellFormed(pin)` | `boolean` — format check only (6 digits); doesn't imply it exists |
| `getState(pin)` | primary state name, or `null` |
| `getDistricts(pin)` | array of every district the pincode touches |
| `getDetails(pin)` | `{ pincode, state, states, stateSource, districts }` |
| `listStates()` | every state/UT name in the dataset |
| `listDistricts(state)` | districts that occur **in that state** (scoped, not global) |
| `getPincodes({ state, district })` | pincodes matching the given filter(s) |
| `preload()` | force an eager data load instead of loading on first call |
| `DATA_VERSION` | dataset snapshot version string, e.g. `"2025.10.03"` |

`getDetails(pin)` returns `state` — the **primary** state for that pincode (the one with
the most post offices; ties broken alphabetically) — and `states`, an array of every
state the pincode actually touches. These differ only for the ~52 pincodes that straddle
a state boundary; for everything else `states` has exactly one entry. `stateSource` tells
you whether the state was read directly from source data or inferred during cleaning.

Keys throughout are **camelCase**, matching Node/JS convention (the Python package uses
snake_case instead — see its own README).

## Requirements

Node **>=20**. Works in any environment that supports modern ESM/CJS interop and has no
Node built-ins requirement (browsers, Deno, Workers, React Native).

## Data freshness

`DATA_VERSION` is the India Post snapshot date this build was compiled from (currently
`2025.10.03`). The upstream dataset hasn't changed content since at least October 2025;
releases of this package are **content-gated**, not calendar-gated — you get a new
snapshot when India Post actually revises the data, not on a fixed monthly schedule.

## Data quality

India Post's own state/district labeling has some gaps and inconsistencies at the
source. This package's build pipeline normalizes state/district names to a single
consistent spelling and backfills a small number of rows with missing state data from
unambiguous evidence, tagging every backfilled row via `stateSource`. Full methodology
and stats: [data/REPORT.md](https://github.com/devzoy/indian-pincode/blob/main/data/REPORT.md).

## License

- **Code:** MIT.
- **Data:** derived from India Post / data.gov.in under the Government Open Data License
  – India (GODL-India), which requires attribution — see [DATA_LICENSE.md](DATA_LICENSE.md).

## Links

- [Full project README](https://github.com/devzoy/indian-pincode) (both languages, both packages, benchmarks, FAQ)
- [Geo companion package](https://www.npmjs.com/package/@devzoy/indian-pincode-geo)
- [v1 → v2 migration guide](https://github.com/devzoy/indian-pincode/blob/main/MIGRATION.md)
- [Report a data issue](https://github.com/devzoy/indian-pincode/issues)
