# Phase 0 — Audit and Baseline

Date of audit: 2026-09-11
Repo state audited: `main` @ `df85708`, latest tag `v1.0.4`.

This document reports the real, verified structure of the project as it exists today, the baseline measurements, data-quality findings, and a confirmed/adjusted plan for Phases 1–6. Numbers were produced on this machine (macOS/arm64, Python 3.13.1, Node v22.22.3). Where the original prompt made an assumption that turned out to be wrong, it is flagged with **CORRECTION**.

---

## 1. Repository map

```
indian-pincode/
├── LICENSE                     MIT (code)
├── README.md                   root readme (marketing-heavy, has errors — see §5)
├── PUBLISHING.md               publish guide (gitignored! — see note below)
├── MANIFEST.in                 includes src/python/indian_pincode/data/*
├── pyproject.toml              PyPI packaging (setuptools), version 1.0.4
├── setup.py                    legacy, version 1.0.0 (STALE — disagrees with pyproject)
├── data.txt                    EMPTY (0 bytes) — dead file
├── data/
│   └── raw-data.csv            SOURCE data, 165,627 data rows (11 columns)
├── dist/                       committed build artifacts of v1.0.4 (should be gitignored)
│   ├── indian_pincode-1.0.4-py3-none-any.whl   9.77 MB
│   └── indian_pincode-1.0.4.tar.gz             15.57 MB
├── src/
│   ├── node/
│   │   ├── index.js            Node library (CommonJS, uses fs/path)
│   │   ├── package.json        @devzoy/indian-pincode v1.0.4, no "files"/"exports"
│   │   ├── test.js             ad-hoc asserts via console.assert
│   │   ├── README.md           node-specific readme (also has errors)
│   │   └── data/
│   │       ├── pincodes.compressed.json   76 KB  (validation index: prefix → suffix[])
│   │       ├── districts.json             9 KB   (flat list of district names)
│   │       ├── geo.json                   472 KB (pincode-level [pin,lat,lng] triples)
│   │       └── details/*.json             39 MB  (405 chunk files, pincode → office[])
│   └── python/
│       └── indian_pincode/
│           ├── __init__.py     Python library (SQLite backend)
│           └── data/
│               ├── pincodes.compressed.json   76 KB  (validation index, same as Node)
│               ├── pincodes.sqlite            31 MB  (used by lookup/search/find_nearby)
│               └── details/*.json             39 MB  (405 files — UNUSED by code, dead weight)
├── tests/
│   └── test_python_lib.py      Python tests (run directly, not pytest)
└── .github/workflows/
    ├── ci.yml
    └── publish.yml
```

### Notable structural issues found
- **No build/pipeline scripts are committed.** The `data/raw-data.csv` → `pincodes.compressed.json` / `pincodes.sqlite` / `details/*.json` / `geo.json` transformation exists nowhere in the repo. The shipped data is unreproducible. This is the single biggest gap and is exactly what Phase 2 fixes.
- **`PUBLISHING.md` is in `.gitignore`.** It is tracked (committed earlier) but ignored for future changes — confusing. Phase 5/6 will fix.
- **`dist/` is committed** even though `.gitignore` lists `dist/`. The v1.0.4 artifacts were force-added. These should not be in git.
- **`setup.py` and `pyproject.toml` disagree** (`1.0.0` vs `1.0.4`) and both configure packaging. `pyproject.toml` is authoritative. Phase 1 removes `setup.py`.
- **`data.txt` is empty** — dead file, safe to delete.
- **Python ships a 39 MB `details/` tree it never reads** (the code only touches `pincodes.sqlite` and `pincodes.compressed.json`). This is duplicated dead weight inflating the wheel.
- Go support was removed in `v1.0.1`, but `PUBLISHING.md` and `ci.yml` comments still mention Go.

---

## 2. Data source

| Field | Value |
| :--- | :--- |
| Dataset | "All India Pincode Directory" (India Post, Dept. of Posts) on data.gov.in |
| Resource ID | `6176ee09-3d56-4a3b-8115-21841576b2f6` |
| API endpoint | `https://api.data.gov.in/resource/6176ee09-3d56-4a3b-8115-21841576b2f6?api-key=<KEY>&format=json&offset=<n>&limit=<n>` |
| API key required? | **Yes.** data.gov.in issues a per-user key; requests without it are rejected. A local CSV path must also be supported (offline builds). |
| Shipped snapshot date | **Unknown.** No metadata/version is stored anywhere in the repo. The data files are dated 2025-11-26 on disk, but that is the processing date, not the source snapshot date. |
| Row count in shipped CSV | 165,627 data rows; 19,586 unique valid pincodes |

Reference: the resource ID and API shape are documented publicly (e.g. a [Stack Overflow answer](https://stackoverflow.com/questions/62425851/india-post-api-how-to-extract-all-pin-codes-from-https-data-gov-in-resources) and the [data.gov.in resource page](https://data.gov.in/resource/all-india-pincode-directory-till-last-month)). *Content rephrased for compliance with licensing restrictions.*

### Data license — **ACTION NEEDED**
The data.gov.in platform publishes under the National Data Sharing and Accessibility Policy (NDSAP), whose license is the **Government Open Data License – India (GODL-India)** ([license PDF](https://data.gov.in/sites/default/files/NDSAP_OpenDataLicense.pdf)). This requires attribution to the source. I have **not** been able to confirm the exact license shown on this specific resource's page (the page is JS-rendered and I could not verify it programmatically). **Before Phase 1 ships a `DATA_LICENSE.md`, please confirm the license string shown on the resource page.** I will leave a clearly-marked TODO rather than guess.

---

## 3. Baseline measurements

### Package size

| Package | Packed / sdist | Unpacked / wheel | Files |
| :--- | :--- | :--- | :--- |
| npm `@devzoy/indian-pincode` (`npm pack --dry-run`) | 2.8 MB | 41.1 MB | 412 |
| PyPI `indian-pincode` (`python -m build`) | sdist 15.57 MB | wheel 9.77 MB | — |

### Cold load time (fresh process, 3 runs)

| Language | Cold load | Note |
| :--- | :--- | :--- |
| Python `import indian_pincode` | ~9–12 ms | loads compressed JSON on import path; SQLite opened lazily per-call |
| Node `require('./index')` | ~0.3–1.0 ms | all data lazy-loaded on first call, so "cold require" understates real first-use cost |

### Operation latency (warm; median / p99)

| Op | Python | Node |
| :--- | :--- | :--- |
| `validate` | 0.0008 ms / 0.0014 ms | 0.0002 ms / 0.0003 ms |
| `lookup` | 0.074 ms / 0.154 ms (opens a **new SQLite connection every call**) | 0.17 ms / 0.27 ms |
| `find_nearby` / `findNearby` (5 km) | 9.9 ms / 12.0 ms | ~6 ms / ~8 ms |

**CORRECTION to the prompt's mental model:** the sub-1ms `validate` figure only covers the format+index check. `find_nearby` is 6–12 ms, not "< 1ms" / "< 10ms optimized" as the README claims. Node's `findNearby` also **re-reads `geo.json` and calls `lookup` (disk read) for every matching point on every call** — there is no spatial index and no memoization of geo data; it is effectively a full scan. Python's `find_nearby` uses a lat/lon `BETWEEN` bounding-box query but opens a fresh connection each call. Both are correctness-preserving but far from the latency the docs imply.

---

## 4. Test results

| Suite | Result | Notes |
| :--- | :--- | :--- |
| `python tests/test_python_lib.py` | **PASS** (4/4) | asserts against `office_name`/`state_name` (SQLite schema) |
| `node src/node/test.js` | **PASS** (weak) | `console.assert` only (never sets exit code on failure); prints `distance_km` which is `undefined` because the real field is `distance`; assertions are loose (`office.includes(...)`) |

Both "pass," but the Node suite would not fail CI on a real regression because `console.assert` does not throw. This is a test-quality gap Phase 4 addresses.

---

## 5. README examples run verbatim

| Example (as written) | Result |
| :--- | :--- |
| Root README Node: `require('indian-pincode')` | **FAILS** — `Cannot find module 'indian-pincode'`. Real package is `@devzoy/indian-pincode`. (This is the known issue.) |
| Node README: `require('@devzoy/indian-pincode')` then `.office/.state/.latitude` | Works, but claimed values are wrong: `searchByDistrict("BANGALORE")` / lookup shows district **`BENGALURU URBAN`** not `BANGALORE`, and office **`Koramangala VI Bk S.O`** not `Koramangala VI Bk SO`. |
| Node `findNearby(...).distance.toFixed(2)` in README vs `distance_km` in test | Field is actually **`distance`**; README is right, the *test* prints the wrong key. |
| Root README Python: `lookup("110001")[0]['office_name']` == "Connaught Place SO" | Field names correct, but **ordering is not guaranteed** — first row is `Baroda House SO`. The "Output:" comments are misleading. |
| Python `find_nearby(28.63,77.21,radius_km=5)[0]['pincode']` == "110001" | Works. |

**Summary:** every "Output:" comment in both READMEs is either wrong or order-dependent, and the flagship Node snippet does not run. Phase 1 + Phase 4 (README-as-tests) fix this.

---

## 6. Data quality profile (from `data/raw-data.csv`, 165,627 rows)

| Check | Count | % of rows |
| :--- | ---: | ---: |
| Rows with missing lat/long (`NA`/empty) | 12,009 | 7.25% |
| Rows with non-numeric coordinates (not `NA`, unparseable) | 6 | 0.004% |
| Rows inside India bbox (lat 6.5–37.5, lon 68.0–97.5) | 151,000 | 91.2% |
| Rows outside bbox | 2,612 | 1.58% |
| — of those, fixable by swapping (lon,lat) | 791 | 0.48% |
| Exact duplicate rows | 2 | — |
| Rows with invalid pincode format (`^[1-9][0-9]{5}$`) | 0 | 0% |
| Unique valid pincodes | 19,586 | — |
| Pincodes mapped to **>1 district** | 1,478 | — |
| District outliers >150 km from district median (districts ≥5 pts) | 6,135 of 150,977 checked | ~4.06% |

### State/UT names
37 distinct `statename` values. Findings:
- **`NA` appears as a state for 715 rows** — and those same rows have `district = NA` too. Spread across many circles (Chhattisgarh 360, Bihar 57, Maharashtra 50, Telangana 46, …). These are unusable for state/district lookup and need a rule (drop, or backfill from circle name).
- The merged UT `THE DADRA AND NAGAR HAVELI AND DAMAN AND DIU` (52 rows) is present — the states mapping table in Phase 2 must handle the legacy split names.
- All other 35 states/UTs look canonical and already uppercase.

### Districts
- **0 pure case/spelling variants** among uppercased district names — the data is already uppercased. A variants mapping file is still worth keeping for genuine renames (e.g. BANGALORE→BENGALURU URBAN, GURGAON→GURUGRAM) that appear in office names/older snapshots.
- 1,478 pincodes span multiple districts (real — pincodes are not 1:1 with districts). The core format **must** support multi-district pincodes, as the prompt requires.

### Office type / delivery enums (already fairly clean)
- `officetype`: `BO` 140,270 · `PO` 24,546 · `HO` 811.
  - **CORRECTION:** the prompt assumed enums `HO/SO/BO`. The raw data uses **`HO/PO/BO`** (Head/Post/Branch Office). "SO" (sub-office) only appears inside office *names* (e.g. "Connaught Place SO"), not in the type column. The Phase 2 enum should be `HO | SO | BO` mapped from the source's `HO | PO | BO` — I'll confirm the intended mapping with you (likely `PO`→`SO`).
- `delivery`: `Delivery` 157,901 · `Non Delivery` 7,726. Clean 2-value enum.

### Coordinate garbage
- Arunachal Pradesh contains at least one absurd longitude (`7506694076.00`) — caught by the bbox rule.
- The proposed bbox (lat 6.5–37.5, lon 68.0–97.5) correctly includes Andaman & Nicobar (lat 7.0–13.3, lon 92.4–93.9), Lakshadweep (lat 8.3–11.7, lon 72.2–73.7), and Arunachal Pradesh (up to lat ~29, lon ~97). Confirmed good defaults.

---

## 7. Output schema comparison (the parity problem)

The two libraries return **different field names and shapes** for the same data — the core reason v2 needs a single pipeline.

| Concept | Python (`lookup`, from SQLite) | Node (`lookup`, from details JSON) |
| :--- | :--- | :--- |
| pincode | `pincode` | *(added by caller; per-office it's the chunk key)* |
| office name | `office_name` | `office` |
| office type | `office_type` | `type` |
| delivery | `delivery_status` | `delivery` |
| division | `division_name` | `division` |
| region | `region_name` | `region` |
| circle | `circle_name` | `circle` |
| taluk | `taluk` | `taluk` |
| district | `district` | `district` |
| state | `state_name` | `state` |
| latitude | `latitude` (REAL) | `lat` (**string**, e.g. `"28.69"`, or `"NA"`) |
| longitude | `longitude` (REAL) | `lng` (**string**) |

Other divergences:
- `find_nearby`/`findNearby` distance field: Python `distance`, Node `distance` — but Node's nearby result rows are built from `lookup` and carry `office/district/state/lat/lng`, while Python's carry `office_name/...`. Not parity-safe.
- `searchDistricts` (Node, list of strings from `districts.json`) vs `search_districts` (Python, `SELECT DISTINCT district` from SQLite) — different data sources, can drift.
- Node has `searchByDistrict` (returns offices); Python has no equivalent.
- Node `validate`/`lookup` are async (return Promises) for `lookup`; Python is sync. The prompt's unified API wants sync core lookups — this is a **breaking change** for Node `lookup`.

---

## 8. Workflows

### `.github/workflows/ci.yml`
- Triggers: push + PR to `main`/`master`.
- `test-python`: matrix Python 3.8/3.9/3.10/3.11 on ubuntu; `pip install -e .`; runs `python tests/test_python_lib.py`.
- `test-node`: matrix Node 14.x/16.x/18.x on ubuntu; `npm ci || npm install` in `src/node`; runs `node src/node/test.js` from repo root.
- Issues: unpinned actions (`actions/checkout@v3`, `setup-python@v4`, `setup-node@v3`); no `permissions:` block; Node 14/16 are EOL; Python 3.12/3.13 not covered; no macOS/Windows; no size/bundle checks.

### `.github/workflows/publish.yml`
- Trigger: GitHub Release `published`.
- `publish-pypi`: `python -m build` then `pypa/gh-action-pypi-publish@release/v1` using **`secrets.PYPI_API_TOKEN`** (long-lived token, not OIDC/Trusted Publishing).
- `publish-npm`: `npm publish --access public` in `src/node` using **`secrets.NPM_TOKEN`** (long-lived, no `--provenance`).
- Issues: long-lived tokens instead of OIDC/Trusted Publishing; no `permissions:` block; unpinned actions; publishes the whole 41 MB Node dir (no `files` whitelist).

---

## 9. Plan confirmation / proposed adjustments for Phases 1–6

The overall plan is sound. Below are the points where reality differs from the prompt and I need a decision, plus confirmations.

### Confirmed as written
- **Phase 1** quick fixes all apply (Node README require path, remove overclaims, fair comparison table, Python floor →3.9, drop `setup.py`, split code/data license). Note: badges say Python 3.6+ / Node 12+ and README claims "100% Uptime", "Zero Data Leakage", "< 1ms" — all confirmed present and will be corrected.
- **Phase 2** pipeline: needed and high-value (no pipeline exists today). Bbox defaults confirmed good. Swap rule will fix ~791 rows; outlier rule (~6,135) and missing (~12,009) will be nulled with `geo_quality` tags.
- **Phase 3** split into core + geo, compact format, unified sync API. Confirmed.
- **Phase 4** golden fixtures + README-as-tests + brute-force geo parity + bundle/size tests. Confirmed and much needed.
- **Phase 5/6** data-refresh + OIDC release workflows + docs rewrite. Confirmed.

### Points that need your decision (please confirm before Phase 1/2)

1. **Data license string (ACTION NEEDED).** I could not verify the exact license on the resource page. I'll ship `DATA_LICENSE.md` with GODL-India attribution and a clearly-marked `TODO: confirm exact license` unless you tell me the exact text.

2. **Office-type enum mapping.** Raw data is `HO/PO/BO`, not `HO/SO/BO`. I propose mapping source `PO`→`SO` (sub-office) so the public enum is `HO | SO | BO`, and documenting it. Confirm, or tell me to keep `PO` verbatim.

3. **`state = NA` / `district = NA` rows (715).** Options: (a) drop them, (b) keep the pincode/office but set state/district to `null`, (c) backfill state from `circlename` (e.g. "Chattisgarh Circle" → CHHATTISGARH). I lean toward (c) for state where the circle is unambiguous, else `null`, and never drop a valid pincode. Confirm preference.

4. **District canonical case.** Prompt says pick uppercase or title case. Data is already uppercase; I propose **UPPERCASE** to avoid a lossy transform and match v1 output. Confirm.

5. **Breaking API change: Node `lookup` becomes synchronous.** The prompt's unified API says core lookups are sync in both languages. v1 Node `lookup`/`findNearby` return Promises. Going sync is the right call but it is a breaking change beyond the listed ones — flagging per your ground rules. (Geo `findNearby` can stay sync too since data is local.) Confirm you're OK making Node `lookup` sync in v2.0.0.

6. **Package names.** Prompt specifies npm `@devzoy/indian-pincode` + `@devzoy/indian-pincode-geo` and PyPI `indian-pincode` + `indian-pincode-geo` with `indian-pincode[geo]` extra. These are new names (`-geo`) that must be claimable on both registries. Confirm the `-geo` names are available/acceptable to you (registry namespace is irreversible once published — but I will not publish; just confirming naming).

7. **`dist/` and `data.txt`.** I plan to remove committed `dist/` artifacts (keep them gitignored) and delete empty `data.txt`. Confirm.

### Proposed split refinement (optional)
The prompt's core/geo split is good. One refinement: put the **pincode→state/district(s)** map and the **validity set** in core (~a few hundred KB), and put **per-office rows + coordinates + spatial index** in geo. The pincode-level centroids (`getCentroid`, `reverseLookup`) belong in **geo**, not core, because they need coordinates. That matches the prompt; just confirming centroids live in geo.

---

## 10. Stop point

Per the ground rules, I'm stopping here and awaiting your go-ahead. Please answer the 7 decisions in §9 (at minimum: data license #1, office enum #2, NA-rows #3, and the Node-sync breaking change #5). Once confirmed, I'll proceed to Phase 1 and commit after each phase.
