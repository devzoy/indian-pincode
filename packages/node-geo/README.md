# @devzoy/indian-pincode-geo

Geo companion for `@devzoy/indian-pincode`: post offices, coordinates, nearby
search, and reverse lookup. Offline, no runtime network calls. **Node-only** (uses
`fs` to load data lazily); it is not intended for browsers. Depends on the core
package.

```js
import geo from '@devzoy/indian-pincode-geo'; // or: const geo = require('@devzoy/indian-pincode-geo')

geo.lookup('110001');                         // [{ pincode, officeName, officeType, ..., geoQuality }]
geo.findNearby(28.63, 77.21, { radiusKm: 5 }); // [ ...{ distanceKm } ], excludes suspect by default
geo.findNearby(28.63, 77.21, { includeSuspect: true });
geo.reverseLookup(28.63, 77.21);              // { pincode: '110001', distanceKm: ... }
geo.getCentroid('110001');                    // { latitude, longitude }
```

Installing this package gives you the full core API plus the geo functions.

Data: derived from India Post / data.gov.in under GODL-India (attribution required).
See DATA_LICENSE.md. Code: MIT.
