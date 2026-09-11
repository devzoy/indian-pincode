# @devzoy/indian-pincode-geo

Geo companion for `@devzoy/indian-pincode`: post offices, coordinates, nearby
search, and reverse lookup. Offline, no runtime network calls. **Node-only** (uses
`fs` to load data lazily); not intended for browsers. Depends on the core package.

Requires Node **>=20**.

```js
const geo = require('@devzoy/indian-pincode-geo'); // ESM: import geo from '@devzoy/indian-pincode-geo'

console.log(geo.lookup('110001')[0].officeName);          // => New Delhi GPO
console.log(geo.lookup('110001')[0].officeType);          // => HO
console.log(geo.findNearby(28.6304, 77.2177, { radiusKm: 2 })[0].officeName); // => Connaught Place SO
console.log(geo.getCentroid('110001') !== null);          // => true
```

`findNearby(lat, lon, { radiusKm = 5, limit = 20, includeSuspect = false })` returns
offices sorted by distance, each with a numeric `distanceKm`. Low-quality ("suspect")
coordinates are excluded unless `includeSuspect: true`. `reverseLookup(lat, lon)` returns
the nearest pincode centroid `{ pincode, distanceKm }`. Every result carries `geoQuality`
and `stateSource`.

Installing this package gives you the full core API plus the geo functions.

Data: derived from India Post / data.gov.in under GODL-India (attribution required).
See DATA_LICENSE.md. Code: MIT.
