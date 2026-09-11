# Migration: v1 → v2

v2 splits the library into a small **core** and an optional **geo** package, unifies
the API across Python and Node, and makes the Node API **synchronous**.

## Install

| | v1 | v2 core | v2 geo |
| :--- | :--- | :--- | :--- |
| Python | `pip install indian-pincode` | `pip install indian-pincode` | `pip install indian-pincode[geo]` |
| Node | `npm i @devzoy/indian-pincode` | `npm i @devzoy/indian-pincode` | `npm i @devzoy/indian-pincode-geo` |

If you only need validation and state/district, install **core**. If you need post
offices, coordinates, nearby search, or reverse lookup, install **geo** (it includes and
re-exports core).

## Breaking changes

### Node: lookup and findNearby are now synchronous
v1 returned Promises; v2 returns values directly.

```js
// v1
const offices = await pincode.lookup('110001');
const near = await pincode.findNearby(28.6, 77.2, 5);

// v2
import geo from '@devzoy/indian-pincode-geo';
const offices = geo.lookup('110001');
const near = geo.findNearby(28.6, 77.2, { radiusKm: 5 });
```

Use `preload()` at startup if you want to pay the data-load cost eagerly.

### Geo functions moved to the geo package
`lookup`, `findNearby`/`find_nearby`, `reverseLookup`/`reverse_lookup`, and
`getCentroid`/`get_centroid` live in the geo package. Calling them from core alone
throws a clear error telling you to install geo.

### Field names: idiomatic casing per language
Object keys are **snake_case in Python** and **camelCase in Node** (this is closer to
v1 Python, which already used `office_name`/`state_name`).

| concept | v1 Python | v1 Node | v2 Python | v2 Node |
| :--- | :--- | :--- | :--- | :--- |
| office name | `office_name` | `office` | `office_name` | `officeName` |
| office type | `office_type` | `type` | `office_type` | `officeType` |
| delivery | `delivery_status` | `delivery` | `delivery_status` | `deliveryStatus` |
| state | `state_name` | `state` | `state` | `state` |
| latitude | `latitude` | `lat` (string) | `latitude` (number) | `latitude` (number) |
| longitude | `longitude` | `lng` (string) | `longitude` (number) | `longitude` (number) |
| nearby distance | `distance` | `distance` | `distance_km` | `distanceKm` |

Every response object also now exposes `geo_quality`/`geoQuality` and
`state_source`/`stateSource`.

### getDetails: `state` (primary) plus `states` (all)
`get_details`/`getDetails` returns both `state` (the **primary** state — the one with
the most post offices for that pincode; ties break alphabetically) and `states` (all
states the pincode touches, sorted). For the ~52 cross-state pincodes these differ; for
everything else `states` has one entry. `districts` lists all districts for the pincode.
`list_districts(state)`/`listDistricts(state)` returns only districts that actually occur
**in that state** (a cross-state pincode no longer leaks another state's districts).

### findNearby options object (Node)
v1: `findNearby(lat, lon, radiusKm)`. v2: `findNearby(lat, lon, { radiusKm, limit, includeSuspect })`.
Python keeps keyword args: `find_nearby(lat, lon, radius_km=5, limit=20, include_suspect=False)`.

### Suspect coordinates excluded by default
Post offices whose coordinates were flagged as low-quality (`geoQuality === 'suspect'`)
are excluded from `findNearby`/`reverseLookup` by default. Pass `includeSuspect: true`
(JS) / `include_suspect=True` (Python) to include them.

### Result ordering is now deterministic
`lookup` results are sorted by office type (HO, PO, BO) then office name. v1 order was
not guaranteed; do not rely on the old order.

### validate() semantics
`validate(pin)` returns true only if the pincode **exists** in the dataset. Use
`isWellFormed` / `is_well_formed` for a format-only (6-digit) check.

## Deprecations (still work, emit a warning)

- Node `searchDistricts(query)` → use `listDistricts(state)` or `getPincodes({ district })`.
- Python `search_districts(query)` → use `list_districts(state)` or `get_pincodes(district=...)`.
- `find_nearby` / `findNearby` keep working with the same positional first args; only the
  options shape (Node) and result field names changed as above.

## New in v2

- `isWellFormed` / `is_well_formed`, `getDetails` / `get_details`, `getPincodes` /
  `get_pincodes`, `getCentroid` / `get_centroid`, `reverseLookup` / `reverse_lookup`,
  `preload`, and the `DATA_VERSION` / `data_version` constant.
- Node core has **no Node built-ins** and works in browsers, bundlers, edge runtimes,
  and React Native.
