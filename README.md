# Indian Pincode

**Offline-first Indian pincode validation, lookup, and geospatial search for Python and Node.js.**

<!-- [![CI](https://github.com/devzoy/indian-pincode/workflows/CI/badge.svg)](https://github.com/devzoy/indian-pincode/actions) -->
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![Node.js](https://img.shields.io/badge/Node.js-20%2B-green)](https://nodejs.org/)

> **Note:** A v2.0 split (small core + optional geo package) is in progress. The examples
> below describe the current v1.x libraries. See [MIGRATION.md](MIGRATION.md) once v2 lands.

## What this is

An embedded dataset of Indian pincodes and post offices (sourced from the India Post
"All India Pincode Directory" on [data.gov.in](https://www.data.gov.in)) plus small
libraries to query it. Lookups run against local data, so there are **no network calls
at runtime** — useful when you want validation and geocoding without depending on a
third-party API's availability or rate limits.

Data snapshot: see the `DATA_VERSION` / `data_version` constant exposed by each package.

## Library vs. self-hosting vs. an API

There is no free lunch — the trade-off is **data freshness and package size** vs. runtime
independence, not just latency.

| Consideration | External API | This library (embedded data) |
| :--- | :--- | :--- |
| Runtime network calls | Required | None (all local) |
| Availability / rate limits | Subject to provider | Not applicable at runtime |
| Data freshness | Provider-managed, can be near-real-time | Fixed to the shipped snapshot; update by upgrading the package |
| Package / install size | Tiny client | Larger (embedded dataset) |
| Lookup latency | Network round-trip (tens–hundreds of ms) | Local (sub-millisecond for validation; single-digit ms for geo search) |
| Privacy | Query leaves your process | Query stays in your process |

If you need always-current data or minimal install size, an API or self-hosting the raw
dataset may fit better. If you want offline, dependency-free lookups and can update on a
release cadence, this library fits well.

## Packages

### Python

**Package**: `indian-pincode`
**Install**: `pip install indian-pincode`

```python
import indian_pincode as pincode

# 1. Validate a pincode (True only if it exists in the dataset)
pincode.validate("110001")   # True
pincode.validate("999999")   # False

# 2. Look up post offices for a pincode
offices = pincode.lookup("110001")
office = offices[0]
office["office_name"]        # e.g. "Baroda House SO"
office["district"]           # "NEW DELHI"
office["state_name"]         # "DELHI"

# 3. Find nearby post offices (within radius_km of a coordinate)
nearby = pincode.find_nearby(28.63, 77.21, radius_km=5)
nearby[0]["pincode"]         # nearest pincode, e.g. "110001"
nearby[0]["distance"]        # distance in km
```

> Field names are `office_name`, `state_name`, `office_type`, `delivery_status`,
> `district`, `latitude`, `longitude`. Result order is not guaranteed in v1.x — do not
> rely on `offices[0]` being a specific office. (v2 sorts results deterministically.)

### Node.js

**Package**: `@devzoy/indian-pincode`
**Install**: `npm install @devzoy/indian-pincode`

CommonJS:

```javascript
const pincode = require('@devzoy/indian-pincode');

// 1. Validate
pincode.validate("560095");   // true
pincode.validate("999999");   // false

// 2. Lookup (returns a Promise in v1.x)
pincode.lookup("560095").then(offices => {
    const o = offices[0];
    console.log(o.office);     // post office name
    console.log(o.district);   // e.g. "BENGALURU URBAN"
    console.log(o.state);      // "KARNATAKA"
});

// 3. Find nearby (returns a Promise in v1.x)
pincode.findNearby(12.93, 77.62, 5).then(results => {
    results.forEach(o => {
        console.log(`${o.pincode} - ${o.office} (${o.distance} km)`);
    });
});
```

ESM:

```javascript
import pincode from '@devzoy/indian-pincode';

const offices = await pincode.lookup("560095");
console.log(offices[0].office);
```

> Node field names are `office`, `state`, `type`, `delivery`, `district`, `latitude`,
> `longitude`; the nearby distance field is `distance`. These differ from the Python
> field names in v1.x — v2 unifies them. See [docs/AUDIT.md](docs/AUDIT.md).

## Contributing

We welcome contributions. To report a data error, open an issue with the pincode and the
expected value. To work on the code:

1. **Fork** and **clone** your fork.
2. **Create a branch**: `git checkout -b feature/your-change`
3. **Commit** and **push**, then **open a Pull Request**.

## License

- **Code:** MIT — see [LICENSE](LICENSE).
- **Data:** derived from India Post / data.gov.in and licensed under the Government Open
  Data License – India (GODL-India), which requires attribution. See
  [DATA_LICENSE.md](DATA_LICENSE.md) for the full attribution text and terms.

## Data source

Data is processed from the "All India Pincode Directory" published by the Department of
Posts, Ministry of Communications, Government of India, on the Open Government Data (OGD)
Platform India. Full attribution is in [DATA_LICENSE.md](DATA_LICENSE.md).
