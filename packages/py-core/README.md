# indian-pincode (core)

Offline-first Indian pincode **validation** and pincode → **state/district** lookup for
Python. No runtime network calls. For post offices, coordinates, and geospatial search,
install the geo extra: `pip install "indian-pincode[geo]"`.

Requires Python **>=3.10**.

## Which package do I need?

| You need… | Install |
| :--- | :--- |
| Validation, pincode → state/district(s), lists | `indian-pincode` (this package) |
| Post offices, coordinates, nearby search, reverse lookup | `indian-pincode[geo]` |

## Usage

```python
import indian_pincode as pincode

print(pincode.validate("110001"))         # True
print(pincode.is_well_formed("999999"))   # True
print(pincode.get_state("560001"))        # KARNATAKA
print(pincode.get_districts("110001"))    # ['NEW DELHI']
```

`get_details(pin)` returns `{pincode, state, states, state_source, districts}` — `state`
is the primary state (most post offices; ties alphabetical) and `states` lists every
state the pincode touches (more than one only for ~52 cross-state pincodes). Also:
`list_states()`, `list_districts(state)`, `get_pincodes(state=..., district=...)`,
`is_well_formed(pin)` (format only) vs `validate(pin)` (exists in the dataset), and
`preload()` to load eagerly. Keys are snake_case.

## Data freshness

`DATA_VERSION` is the India Post snapshot date (currently `2025.10.03`, from the
dataset's `updated_date`). Upstream content has not changed since October 2025; releases
are content-gated, so the data updates when India Post actually revises it — not on a
fixed monthly cadence.

## License

- **Code:** MIT.
- **Data:** derived from India Post / data.gov.in under GODL-India (attribution
  required) — see [DATA_LICENSE.md](DATA_LICENSE.md).
