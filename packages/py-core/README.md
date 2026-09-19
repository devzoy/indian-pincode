# indian-pincode (core)

**Offline-first Indian pincode validation and pincode → state/district lookup for
Python.**

[![PyPI](https://img.shields.io/pypi/v/indian-pincode)](https://pypi.org/project/indian-pincode/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

No runtime network calls — the dataset is embedded in the package at build time. For
post offices, coordinates, and geospatial search, install the geo extra:
`pip install "indian-pincode[geo]"`. That pulls in
[`indian-pincode-geo`](https://pypi.org/project/indian-pincode-geo/), which re-exports
everything in this package plus geo functions.

## Which package do I need?

| You need… | Install |
| :--- | :--- |
| Validation, pincode → state/district(s), lists | `indian-pincode` (this package) |
| Post offices, coordinates, nearby search, reverse lookup | `indian-pincode[geo]` |

## Install

```bash
pip install indian-pincode
```

## Usage

```python
import indian_pincode as pincode

pincode.validate("110001")                     # True  — exists in the dataset
pincode.is_well_formed("999999")                 # True  — well-formed 6-digit code, format only
pincode.get_state("560001")                      # "KARNATAKA"
pincode.get_details("682555")["state"]           # "LAKSHADWEEP"
pincode.get_districts("110025")                  # ["BUDAUN", "SOUTH", "SOUTH EAST"] — cross-state pincode
pincode.list_states()                            # 36 states/UTs
pincode.list_districts("KERALA")[:3]             # ["ALAPPUZHA", "ERNAKULAM", "IDUKKI"]
pincode.get_pincodes(state="GOA")                # every pincode in Goa
```

## API reference

| Function | Returns |
| :--- | :--- |
| `validate(pin)` | `bool` — pincode exists in the dataset |
| `is_well_formed(pin)` | `bool` — format check only (6 digits); doesn't imply it exists |
| `get_state(pin)` | primary state name, or `None` |
| `get_districts(pin)` | list of every district the pincode touches |
| `get_details(pin)` | `{pincode, state, states, state_source, districts}` |
| `list_states()` | every state/UT name in the dataset |
| `list_districts(state)` | districts that occur **in that state** (scoped, not global) |
| `get_pincodes(state=None, district=None)` | pincodes matching the given filter(s) |
| `preload()` | force an eager data load instead of lazy-loading on first call |
| `DATA_VERSION` | dataset snapshot version string, e.g. `"2025.10.03"` |

`get_details(pin)` returns `state` — the **primary** state for that pincode (the one
with the most post offices; ties broken alphabetically) — and `states`, a list of every
state the pincode actually touches. These differ only for the ~52 pincodes that straddle
a state boundary; for everything else `states` has exactly one entry. `state_source`
tells you whether the state was read directly from source data or inferred during
cleaning.

Keys throughout are **snake_case**, matching Python convention (the Node package uses
camelCase instead — see its own README).

## Requirements

Python **>=3.10**.

## Data freshness

`DATA_VERSION` is the India Post snapshot date this build was compiled from (currently
`2025.10.03`, read from the dataset's `updated_date` field). The upstream dataset hasn't
changed content since at least October 2025; releases of this package are
**content-gated**, not calendar-gated — you get a new snapshot when India Post actually
revises the data, not on a fixed monthly schedule.

## Data quality

India Post's own state/district labeling has some gaps and inconsistencies at the
source. This package's build pipeline normalizes state/district names to a single
consistent spelling and backfills a small number of rows with missing state data from
unambiguous evidence, tagging every backfilled row via `state_source`. Full methodology
and stats: [data/REPORT.md](https://github.com/devzoy/indian-pincode/blob/main/data/REPORT.md).

## License

- **Code:** MIT.
- **Data:** derived from India Post / data.gov.in under the Government Open Data License
  – India (GODL-India), which requires attribution — see [DATA_LICENSE.md](DATA_LICENSE.md).

## Links

- [Full project README](https://github.com/devzoy/indian-pincode) (both languages, both packages, benchmarks, FAQ)
- [Geo companion package](https://pypi.org/project/indian-pincode-geo/)
- [v1 → v2 migration guide](https://github.com/devzoy/indian-pincode/blob/main/MIGRATION.md)
- [Report a data issue](https://github.com/devzoy/indian-pincode/issues)
