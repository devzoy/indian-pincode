# @devzoy/indian-pincode (core)

Offline-first Indian pincode validation and pincode → state/district lookup.
No runtime network calls, no Node built-ins — works in Node, browsers, bundlers
(Vite/webpack/esbuild), edge runtimes, and React Native. For post offices and
geospatial search, add `@devzoy/indian-pincode-geo`.

```js
import pincode from '@devzoy/indian-pincode'; // or: const pincode = require('@devzoy/indian-pincode')

pincode.validate('110001');        // true (exists)
pincode.isWellFormed('999999');    // true (format only)
pincode.getDetails('110001');      // { pincode: '110001', state: 'DELHI', districts: ['NEW DELHI'] }
pincode.getState('560001');        // 'KARNATAKA'
pincode.listStates();              // [...]
pincode.getPincodes({ state: 'GOA' });
pincode.DATA_VERSION;              // 'YYYY.MM.DD'
```

Data: derived from India Post / data.gov.in under GODL-India (attribution required).
See DATA_LICENSE.md. Code: MIT.
