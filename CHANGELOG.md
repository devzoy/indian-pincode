# Changelog

All notable changes to this project are documented here. This project follows
[Semantic Versioning](https://semver.org/). Data-refresh releases are patch bumps and are
content-gated (see [Data freshness](README.md#data-freshness)).

## 2.1.0 — 2026-09-19

### Fixed
- **`reverse_lookup`/`reverseLookup` could return the wrong pincode** (both Python
  and Node). The expanding nearest-neighbor search stopped at the first non-empty
  search box and returned the closest point *within that box* — but a genuinely
  closer point can sit just outside the box, near a corner (a box's corners are
  ~1.41x farther from center than its edges). Verified against a brute-force
  haversine scan over all 19,416 centroids on 2,000+ points perturbed near real
  centroids (exactly where this bug bites): Python was wrong on ~1.25-2% of
  queries before the fix, 0/2000 after; Node's structurally identical bug wasn't
  observed to trigger in that same test but was fixed on the same principle
  regardless, since it was reachable in theory. Both languages now do a
  guaranteed-correct verification pass sized to the found distance before
  returning. Regression tests added (`test_reverse_lookup_matches_brute_force_near_real_centroids`,
  `reverseLookup == brute force near 2000 real centroids`).
- Monorepo root `package.json` version had drifted from `version.json`
  (`2.0.0` vs `2.0.1`) because `scripts/propagate_version.py` never touched it.
  Fixed the drift and added it as a 5th managed manifest so this can't recur.
- README accuracy table incorrectly listed pincode `682555` as a "cross-state"
  example — it's actually a single-state Lakshadweep pincode. Replaced with
  `110025`, and added an explicit note that some multi-state entries are
  source-data mis-codings (a single office mis-tagged to the wrong district),
  not genuine state-boundary pincodes — see the new Data quality note in
  [README.md](README.md#data-quality).

### Added
- `reverse_lookup(lat, lon, max_km=None)` / `reverseLookup(lat, lon, maxKm)`: an
  optional distance cap. Without it, `reverse_lookup` always returns *some*
  pincode, even for coordinates far out at sea — `max_km` returns `None` instead
  once the nearest match exceeds that distance.

### Known gaps (tracked, not fixed this release)
- State/district assignment gets no outlier treatment analogous to coordinate
  `geo_quality` flagging — a single office reporting a state far from the rest
  of its pincode's offices (see the `110025`/Budaun example above) isn't
  currently flagged as low-confidence the way suspect coordinates are.
- `get_details`/`getDetails` returns `districts` as a flat list without saying
  which state each district belongs to for multi-state pincodes.

## 2.0.1 — 2026-09-19

Docs-only release. No API or data changes.

- Rewrote all five READMEs (root + 4 package READMEs) with full API reference tables,
  verified example outputs, an honest library-vs-API comparison, accuracy examples, a
  data-quality section, and an FAQ — previous package-page READMEs were too thin to be
  useful on their own on npm/PyPI.
- Removed `docs/AUDIT.md`, an internal planning document from the v2 rebuild that had no
  further purpose once its findings were resolved.

## 2.0.0 — 2026-09-19

A ground-up rework. **Breaking**; see [MIGRATION.md](MIGRATION.md).

### Packages
- Split into a small **core** and an optional **geo** package on each registry:
  - PyPI: `indian-pincode` (core), `indian-pincode-geo` (geo); install geo via
    `pip install "indian-pincode[geo]"`.
  - npm: `@devzoy/indian-pincode` (core), `@devzoy/indian-pincode-geo` (geo).
- geo depends on the **exact** core version; a runtime warning fires on a version
  mismatch. A single `version.json` propagates to all four manifests.

### API
- Unified, **synchronous** API across both languages (Node `lookup`/`findNearby` are no
  longer Promises). Object keys are snake_case in Python, camelCase in Node.
- Core: `validate` (existence, not just format), `isWellFormed`/`is_well_formed`,
  `getDetails`/`get_details` (now returns primary `state` **plus** `states` and
  `stateSource`/`state_source`), `getState`, `getDistricts`, `listStates`,
  `listDistricts`, `getPincodes`/`get_pincodes`, `preload`, `DATA_VERSION`.
- Geo: `lookup`, `findNearby`/`find_nearby`, `reverseLookup`/`reverse_lookup`,
  `getCentroid`/`get_centroid`. Every result exposes `geoQuality`/`geo_quality` and
  `state_source`. `findNearby` excludes `suspect` coordinates by default
  (`includeSuspect`/`include_suspect` to include).
- v1 names kept as deprecation shims (`searchDistricts`/`search_districts`).

### Data pipeline (new)
- Reproducible build: `python -m pipeline.build` fetches (API, key from
  `DATA_GOV_IN_API_KEY`, never logged/argv'd), or reads a local CSV, or a manual
  `--from-csv`. Deterministic, byte-stable outputs.
- Normalization: canonical state/UT names, UPPERCASE districts, `HO/PO/BO` and delivery
  enums, exact-duplicate removal, NA-state backfill (`state_source`).
- Coordinate cleaning: bounding box, lat/long swap correction, adaptive outlier flagging
  (`geo_quality = "suspect"`), per-pincode centroids.
- Sanity gates (pincode ±3%, post office ±5%, no zero-pincode state, <20% null coords)
  with an auditable `data/REPORT.md`.
- `content_sha256` in `metadata.json` drives content-gated refreshes.

### Correctness
- Fixed a cross-state district leak (e.g. `listDistricts('DELHI')` no longer returns the
  UP district `BUDAUN` via cross-state pincode `110025`); districts are stored as
  `(district, state)` pairs.

### Sizes (v1 → v2, unpacked)
- npm core: 41.1 MB → ~208 KB. PyPI core wheel data: 9.77 MB → ~204 KB.
- geo: npm ~2.7 MB, PyPI SQLite ~9.8 MB.

### Packaging & CI
- Node: dual CJS/ESM, `exports` map, `.d.ts`, `sideEffects: false`, single embedded data
  module, no Node built-ins in core (browser/bundler/edge/RN safe).
- Python: `py.typed`, type hints, read-only immutable SQLite via `importlib.resources`.
- CI matrix (Python 3.10–3.14, Node 20/22/24; Ubuntu + macOS/Windows), golden-fixture
  parity tests, README-as-tests, size-budget and bundler checks, SHA-pinned actions.
- Release via OIDC trusted publishing (PyPI + npm `--provenance`), no long-lived tokens;
  monthly content-gated data-refresh workflow.

### Data
- Snapshot `2025.10.03` (India Post via data.gov.in): 19,586 pincodes, 165,625 post
  offices. GODL-India data license documented in `DATA_LICENSE.md`.

## 1.0.4 and earlier

v1 line: single package per registry, SQLite (Python) / lazy JSON chunks (Node),
~10–40 MB installs, async Node API. See git history.
