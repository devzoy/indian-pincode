# @devzoy/indian-pincode (core)

Offline-first Indian pincode validation and pincode → state/district lookup.
No runtime network calls, no Node built-ins — works in Node, browsers, bundlers
(Vite/webpack/esbuild), edge runtimes, and React Native. For post offices and
geospatial search, add `@devzoy/indian-pincode-geo`.

```js
const pincode = require('@devzoy/indian-pincode'); // ESM: import pincode from '@devzoy/indian-pincode'

console.log(pincode.validate('110001'));            // => true
console.log(pincode.isWellFormed('999999'));        // => true
console.log(pincode.getState('560001'));            // => KARNATAKA
console.log(pincode.getDetails('110001').districts); // => NEW DELHI
```

Requires Node **>=20**. Keys are camelCase. `getDetails(pin)` returns
`{ pincode, state, states, stateSource, districts }` — `state` is the primary state
(most post offices; ties alphabetical), `states` lists all states the pincode touches.
Also: `isWellFormed` (format only) vs `validate` (exists in the dataset), `listStates`,
`listDistricts(state)`, `getPincodes({ state, district })`, `preload()`, `DATA_VERSION`.

**Data freshness:** `DATA_VERSION` is the India Post snapshot date (currently
`2025.10.03`). Upstream content hasn't changed since October 2025; releases are
content-gated, not monthly.

Data: derived from India Post / data.gov.in under GODL-India (attribution required).
See [DATA_LICENSE.md](DATA_LICENSE.md). Code: MIT.
