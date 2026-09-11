# Data pipeline

Single build pipeline that turns the India Post "All India Pincode Directory"
(data.gov.in) into the canonical dataset that both the Python and Node packages are
generated from (Phase 3). One data source, two outputs — so the libraries always agree.

## Run

```bash
# Reproduce from the committed local CSV (no network).
# A source date is required because the pipeline never guesses it.
python -m pipeline.build --source-date DD/MM/YYYY

# Fresh fetch from data.gov.in (needs an API key; never logged).
export DATA_GOV_IN_API_KEY=...   # from https://data.gov.in (account -> API key)
python -m pipeline.build --fetch
```

If `--fetch` is passed but `DATA_GOV_IN_API_KEY` is unset, the fetch is skipped
(not an error) and the local CSV is used.

## Options

- `--fetch` — fetch all pages from the API and verify the count against the API total.
- `--local-csv PATH` — use a specific local CSV (default `data/raw-data.csv`).
- `--source-date DD/MM/YYYY` — required for local builds; the source `updated_date`.
- `--no-enforce-gates` — warn instead of failing on a sanity-gate violation.
- `--sibling-flag-km`, `--district-hard-km` — override outlier thresholds.

All other thresholds live in `pipeline/config.py` (`Thresholds`).

## Steps

1. **Fetch** (`fetch.py`) — API (paginated, retry+backoff, key from env, never logged)
   or local file. Saves raw + SHA-256 + timestamp to `pipeline/raw/` (gitignored).
2. **Normalize** (`normalize.py`) — schema gate (11 columns), whitespace, pincode
   `^[1-9][0-9]{5}$`, state canonicalization (`mappings/states.json`), NA-state backfill
   (sibling → single-state circle → null, recorded in `state_source`), district
   uppercase + variants (`mappings/districts.json`), office type `HO|PO|BO` and delivery
   enums, exact-duplicate removal.
3. **Coordinates** (`coordinates.py`) — parse, partial→missing, bbox, swap, remove,
   sibling/district outlier flagging (`geo_quality="suspect"`), per-pincode centroids.
4. **Gates** (`gates.py`) — pincode ±3%, post office ±5%, no zero-pincode state,
   <20% null coords. Configurable.
5. **Outputs** (`outputs.py`) — `data/build/pincodes.normalized.jsonl.gz` (canonical),
   `data/build/centroids.json.gz`, `data/build/metadata.json`, and `data/REPORT.md`.

## Mappings

- `mappings/states.json` — canonical state/UT list + legacy/merged aliases.
- `mappings/circles.json` — single-state circles safe for backfill; multi-state circles
  explicitly excluded.
- `mappings/districts.json` — known district rename/spelling variants.
