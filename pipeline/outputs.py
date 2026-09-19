"""Output writers: canonical JSONL, metadata.json, and the human-readable REPORT.md."""

from __future__ import annotations

import json
import os
import statistics
from collections import defaultdict
from typing import Dict, List, Optional

from . import config
from .coordinates import haversine_km


_NORMALIZED_FIELDS = [
    "pincode", "office_name", "office_type", "delivery_status",
    "division_name", "region_name", "circle_name", "district",
    "state_name", "state_source", "state_inferred_from_circle",
    "latitude", "longitude", "geo_quality", "geo_fixed",
]


def _content_sort_key(row: Dict):
    """Explicit, documented TOTAL ordering for content hashing.

    Primary keys: pincode, office_name, office_type. Then the remaining
    normalized fields in a fixed order, so the ordering is total even when two
    offices share pincode+name+type. `None` sorts before any string via the
    (is-not-None, value) pair trick."""
    primary = ("pincode", "office_name", "office_type")
    rest = [f for f in _NORMALIZED_FIELDS if f not in primary]
    key = []
    for f in primary + tuple(rest):
        v = row.get(f)
        # normalize to a comparable (type_rank, str) tuple so None/str/number mix safely
        if v is None:
            key.append((0, ""))
        else:
            key.append((1, str(v)))
    return key


def content_sha256(rows: List[Dict]) -> str:
    """SHA-256 of the normalized CONTENT, independent of input row order.

    Rows are sorted by an explicit total ordering (pincode, office_name,
    office_type, then the remaining normalized fields) BEFORE hashing, so the hash
    depends only on the cleaned data, not on the source file's row order or any
    shuffling. The refresh workflow uses this to decide whether to open a PR."""
    import hashlib

    ordered = sorted(rows, key=_content_sort_key)
    h = hashlib.sha256()
    for row in ordered:
        out = {k: row.get(k) for k in _NORMALIZED_FIELDS}
        h.update((json.dumps(out, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"))
    return h.hexdigest()


def write_normalized(rows: List[Dict], centroids: Dict, path: str = config.NORMALIZED_PATH) -> None:
    """Write the canonical dataset as gzipped JSONL (one object per line).

    Gzip keeps this source-of-truth file small enough to commit (~3.5 MB vs ~64 MB
    raw) while remaining diff-friendly line-by-line after decompression.
    """
    import gzip

    os.makedirs(os.path.dirname(path), exist_ok=True)
    # mtime=0 for reproducible gzip output (byte-stable across runs of same data).
    with gzip.GzipFile(path, "wb", mtime=0) as gz:
        for row in rows:
            out = {k: row.get(k) for k in _NORMALIZED_FIELDS}
            line = json.dumps(out, ensure_ascii=False, sort_keys=True) + "\n"
            gz.write(line.encode("utf-8"))
    # centroids sidecar (gzipped)
    with gzip.GzipFile(config.CENTROIDS_PATH, "wb", mtime=0) as gz:
        gz.write(json.dumps(centroids, ensure_ascii=False, sort_keys=True).encode("utf-8"))


def build_metadata(
    rows: List[Dict],
    fetch_result,
    norm_stats: Dict,
    coord_stats: Dict,
    gate_result: Dict,
    source_updated_date: str,
) -> Dict:
    data_version = source_updated_date.replace("-", ".")  # YYYY.MM.DD
    pincodes = set(r["pincode"] for r in rows)
    attribution = (
        "Department of Posts, Ministry of Communications, Government of India, 2020, "
        "All India Pincode Directory till last month, Open Government Data (OGD) "
        f"Platform India, {_ddmmyyyy(source_updated_date)}, "
        "https://www.data.gov.in/resource/all-india-pincode-directory-till-last-month. "
        "Released under NDSAP and licensed under Government Open Data License - India: "
        "https://www.data.gov.in/Godl"
    )
    return {
        "data_version": data_version,
        "source_updated_date": source_updated_date,
        # Hash of the cleaned/normalized content. The refresh workflow opens a PR
        # only when THIS changes, never on source dates alone.
        "content_sha256": content_sha256(rows),
        "source": {
            "resource_id": config.RESOURCE_ID,
            "sha256": fetch_result.sha256 if fetch_result else None,
            # `origin` (api/local) is run-time provenance and lives in build_log.json,
            # not here, so committed metadata is byte-stable regardless of how the
            # identical source bytes were obtained.
        },
        "counts": {
            "pincode_count": len(pincodes),
            "post_office_count": len(rows),
            "input_rows": norm_stats["input_rows"],
            "invalid_pincode_dropped": norm_stats["invalid_pincode_dropped"],
            "exact_duplicates_removed": norm_stats["exact_duplicates_removed"],
        },
        "state_source": norm_stats["state_source"],
        "na_backfill": norm_stats["na_backfill"],
        "coordinate_stats": {k: v for k, v in coord_stats.items() if k != "flagged_samples"},
        "gates": gate_result,
        "attribution": attribution,
    }


def write_metadata(meta: Dict, path: str = config.METADATA_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2, sort_keys=True)


def _ddmmyyyy(iso: str) -> str:
    y, m, d = iso.split("-")
    return f"{d}/{m}/{y}"


# ---- Report ----------------------------------------------------------------

def write_report(
    rows: List[Dict],
    meta: Dict,
    norm_stats: Dict,
    coord_result: Dict,
    v1_reproduction_diff: Dict,
    fresh_diff: Optional[Dict],
    path: str = config.REPORT_PATH,
) -> None:
    coord_stats = coord_result["stats"]
    lines: List[str] = []
    A = lines.append

    A("# Data Build Report")
    A("")
    A(f"- **data_version:** `{meta['data_version']}`")
    A(f"- **source_updated_date:** `{meta['source_updated_date']}` (as reported by the API)")
    A(f"- **content_sha256:** `{meta['content_sha256']}` "
      "(hash of the normalized data; drives refresh PRs)")
    A(f"- **source SHA-256:** `{meta['source']['sha256']}`")
    A("")
    A("_Note: this report is derived only from the source data and is byte-stable "
      "across re-runs on the same source. Run-time details (fetch time, duration) "
      "are written to the gitignored `pipeline/raw/build_log.json`._")
    A("")

    A("## Counts")
    A("")
    A("| Metric | Value |")
    A("| :--- | ---: |")
    A(f"| Input rows | {norm_stats['input_rows']} |")
    A(f"| Invalid pincode rows dropped | {norm_stats['invalid_pincode_dropped']} |")
    A(f"| Exact duplicate rows removed | {norm_stats['exact_duplicates_removed']} |")
    A(f"| Output post office rows | {meta['counts']['post_office_count']} |")
    A(f"| Unique pincodes | {meta['counts']['pincode_count']} |")
    A("")

    A("## State backfill (NA rows)")
    A("")
    A("| state_source | rows |")
    A("| :--- | ---: |")
    for k, v in sorted(meta["state_source"].items()):
        A(f"| {k} | {v} |")
    A("")
    A(f"Backfill paths: inferred_pincode={meta['na_backfill']['inferred_pincode']}, "
      f"inferred_circle={meta['na_backfill']['inferred_circle']}, "
      f"null={meta['na_backfill']['null']}.")
    A("")
    cbc = norm_stats.get("circle_backfill_by_circle")
    if cbc:
        A("Circle-inferred rows, by the (strictly single-state) circle used:")
        A("")
        A("| circle | canonical state | rows |")
        A("| :--- | :--- | ---: |")
        for circ, cnt in sorted(cbc.items()):
            # canonical state resolved by the same mapping the pipeline used
            A(f"| {circ} | (single-state) | {cnt} |")
        A("")
    if norm_stats.get("circle_backfill_rejected"):
        A(f"Circles rejected from backfill (no longer strictly single-state): "
          f"{norm_stats['circle_backfill_rejected']}")
        A("")
    daa = norm_stats.get("district_aliases_applied")
    A("District rename/variant mappings applied (only entries whose source spelling "
      "actually appears in the data):")
    if daa:
        A("")
        A("| mapping | rows |")
        A("| :--- | ---: |")
        for m, cnt in sorted(daa.items()):
            A(f"| {m} | {cnt} |")
        A("")
    else:
        A(" none.")
        A("")
    if norm_stats.get("unknown_state_kept"):
        A(f"Unknown (non-NA, unmapped) states kept as-is: {norm_stats['unknown_state_kept']}")
        A("")
    if norm_stats.get("unknown_office_type"):
        A(f"Unknown office types seen: {norm_stats['unknown_office_type']}")
        A("")
    if norm_stats.get("unknown_delivery"):
        A(f"Unknown delivery statuses seen: {norm_stats['unknown_delivery']}")
        A("")

    A("## Coordinate cleaning")
    A("")
    A("| Rule | Count |")
    A("| :--- | ---: |")
    A(f"| Both missing/NA/non-numeric -> null (missing) | {coord_stats['parsed_null']} |")
    A(f"| Partial (one of lat/lon null) -> null (missing) | {coord_stats['partial_missing']} |")
    A(f"| In-box original | {coord_stats['in_box_original']} |")
    A(f"| Swapped (lon,lat) -> valid | {coord_stats['swapped']} |")
    A(f"| Removed (out of box, swap did not help / garbage) | {coord_stats['removed_out_of_box']} |")
    A(f"| Suspect via sibling-median rule | {coord_stats['suspect_sibling']} |")
    A(f"| Suspect via district-median fallback | {coord_stats['suspect_district']} |")
    A("")
    A("geo_quality distribution:")
    A("")
    A("| geo_quality | rows |")
    A("| :--- | ---: |")
    for k in ["original", "swapped", "suspect", "removed", "missing"]:
        A(f"| {k} | {coord_stats['geo_quality'].get(k, 0)} |")
    A("")

    # Outlier distance distribution + samples
    _write_outlier_section(A, rows, coord_result)

    # Multi-district and prefix-mismatch sections (report only)
    _write_multi_district_section(A, rows)

    # v1.0.4 reproduction diff
    A("## v1.0.4 reproduction diff")
    A("")
    A("Comparison of this build (run against the committed `data/raw-data.csv`) versus "
      "the v1.0.4 baseline counts recorded in the Phase 0 audit.")
    A("")
    A("| Metric | v1.0.4 | this build | delta |")
    A("| :--- | ---: | ---: | ---: |")
    for k, label in [("pincode_count", "Unique pincodes"),
                     ("post_office_count", "Post office rows")]:
        old = v1_reproduction_diff["previous"].get(k)
        new = v1_reproduction_diff["current"].get(k)
        delta = (new - old) if (old is not None and new is not None) else "n/a"
        A(f"| {label} | {old} | {new} | {delta} |")
    A("")
    A(f"Pincodes added vs v1.0.4 set: {v1_reproduction_diff['pincodes_added']}; "
      f"removed: {v1_reproduction_diff['pincodes_removed']}.")
    A("")

    # fresh-fetch diff
    A("## Fresh-fetch diff")
    A("")
    if fresh_diff is None:
        A("_No fresh fetch was performed (DATA_GOV_IN_API_KEY not set or --fetch not "
          "passed). Run `python -m pipeline.build --fetch` with the key to populate this._")
    elif not fresh_diff.get("available"):
        A("_Fresh fetch performed, but no previously-committed build was available "
          "to diff against._")
    else:
        A("Fresh build vs the previously-committed build (from git HEAD).")
        A("")
        A("| Metric | previous | fresh | delta |")
        A("| :--- | ---: | ---: | ---: |")
        for k, label in [("pincode_count", "Unique pincodes"),
                         ("post_office_count", "Post office rows")]:
            old = fresh_diff["previous"].get(k)
            new = fresh_diff["fresh"].get(k)
            A(f"| {label} | {old} | {new} | {new - old:+d} |")
        A("")
        A(f"Pincodes added: **{fresh_diff['pincodes_added']}**, "
          f"removed: **{fresh_diff['pincodes_removed']}**. "
          f"Post offices delta: **{fresh_diff['post_offices_delta']:+d}**. "
          f"Pincodes whose state/district set changed: **{fresh_diff['pincodes_sd_changed']}**.")
        A("")
        A(f"New states: {fresh_diff['new_states'] or 'none'}. "
          f"New districts: {len(fresh_diff['new_districts'])} "
          f"({fresh_diff['new_districts'][:10]}{'...' if len(fresh_diff['new_districts'])>10 else ''}).")
        A("")
        if fresh_diff["pincodes_added_samples"]:
            A(f"Sample added pincodes: {fresh_diff['pincodes_added_samples']}")
            A("")
        if fresh_diff["pincodes_removed_samples"]:
            A(f"Sample removed pincodes: {fresh_diff['pincodes_removed_samples']}")
            A("")
        if fresh_diff["pincodes_sd_changed_samples"]:
            A(f"Sample state/district-changed pincodes: {fresh_diff['pincodes_sd_changed_samples']}")
            A("")
    A("")

    # Sanity gates
    A("## Sanity gates")
    A("")
    A("| Gate | Result | Detail |")
    A("| :--- | :--- | :--- |")
    for g in meta["gates"]["results"]:
        status = "PASS"
        if not g["ok"]:
            status = "FAIL"
        elif g.get("warning"):
            status = "WARN (waived)"
        A(f"| {g['gate']} | {status} | {g['detail']} |")
    A("")
    if meta["gates"].get("baseline_change_waiver"):
        A(f"**Baseline-change waiver active:** {meta['gates']['baseline_change_waiver']}")
        A("")

    # Attribution
    A("## Attribution")
    A("")
    A("> " + meta["attribution"])
    A("")

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _write_outlier_section(A, rows, coord_result):
    coord_stats = coord_result["stats"]
    # Recompute the distance distribution of suspect rows for the histogram.
    samples = coord_stats.get("flagged_samples", [])
    A("## Outlier sanity check")
    A("")
    total_suspect = coord_stats["geo_quality"].get("suspect", 0)
    A(f"Total suspect rows: {total_suspect} "
      f"(sibling rule: {coord_stats['suspect_sibling']}, "
      f"district fallback: {coord_stats['suspect_district']}).")
    A("")

    dd = coord_stats.get("sibling_distance_distribution")
    if dd:
        A(f"**Adaptive outlier rule (sibling branch):** {dd['rule']}. "
          f"n={dd['n']} offices evaluated against their same-pincode siblings.")
        A("")
        A("| percentile | distance (km) |")
        A("| :--- | ---: |")
        for k in ["p50", "p75", "p90", "p95", "p99"]:
            A(f"| {k} | {dd[k]} |")
        A(f"| max | {dd['max']} |")
        A("")
        A("| threshold | rows exceeding | % of evaluated |")
        A("| :--- | ---: | ---: |")
        for t in ["25", "40", "50", "75", "100", "150", "200"]:
            c = dd["over_km"][t]
            A(f"| > {t} km | {c} | {c / dd['n'] * 100:.2f}% |")
        A("")

    # Old vs new rule comparison.
    total = _total_rows(rows)
    new_sibling = coord_stats["suspect_sibling"]
    legacy_sibling = coord_stats.get("legacy_suspect_sibling", 0)
    A("**New adaptive rule vs legacy fixed-50 km rule (sibling branch):**")
    A("")
    A("| rule | flagged (sibling) | % of all rows |")
    A("| :--- | ---: | ---: |")
    A(f"| legacy: > 50 km | {legacy_sibling} | {legacy_sibling / total * 100:.2f}% |")
    A(f"| new: max(40 km, 5x spread), hard 150 km | {new_sibling} | {new_sibling / total * 100:.2f}% |")
    A("")
    A(f"Rows flagged ONLY by the new rule: {coord_stats.get('new_only_count', 0)}. "
      f"Rows suspect under 50 km but NO LONGER flagged: {coord_stats.get('legacy_only_count', 0)}.")
    A("")

    _sample_table(A, "10 rows flagged ONLY by the new adaptive rule",
                  coord_stats.get("new_only_samples", []))
    _sample_table(A, "10 rows that were suspect at 50 km but are no longer flagged",
                  coord_stats.get("legacy_only_samples", []))
    A("> Suspects are flagged, not deleted: findNearby excludes them by default but "
      "`includeSuspect` recovers them, and pincode centroids ignore them.")
    A("")
    _sample_table(A, "20 random rows flagged as suspect (either rule)", samples)


def _total_rows(rows) -> int:
    return max(1, len(rows))


def _sample_table(A, title, samples):
    A(f"**{title}:**")
    A("")
    if not samples:
        A("_(none)_")
        A("")
        return
    A("| pincode | office | state | district | lat | lon | rule | dist_km |")
    A("| :--- | :--- | :--- | :--- | ---: | ---: | :--- | ---: |")
    for s in samples:
        A(f"| {s['pincode']} | {s['office_name']} | {s['state_name']} | "
          f"{s['district']} | {s['latitude']} | {s['longitude']} | {s['reason']} | "
          f"{s['distance_km']} |")
    A("")


def _write_multi_district_section(A, rows):
    # pincode -> set of (state, district)
    pin_pairs = defaultdict(set)
    pin_states = defaultdict(set)
    for r in rows:
        pin_pairs[r["pincode"]].add((r["state_name"], r["district"]))
        if r["state_name"]:
            pin_states[r["pincode"]].add(r["state_name"])

    multi_district = {p: v for p, v in pin_pairs.items() if len({d for _, d in v}) > 1}
    multi_state = {p: v for p, v in pin_states.items() if len(v) > 1}

    A("## Multi-district / cross-state pincodes (report only, not modified)")
    A("")
    A(f"Pincodes mapped to more than one district: {len(multi_district)}.")
    A(f"Pincodes whose districts span more than one STATE (possible source errors): "
      f"{len(multi_state)}.")
    A("")
    if multi_state:
        A("Sample cross-state pincodes:")
        A("")
        A("| pincode | states |")
        A("| :--- | :--- |")
        for p in sorted(multi_state)[:20]:
            A(f"| {p} | {sorted(multi_state[p])} |")
        A("")

    # prefix mismatch: state outside the allowed set for the pincode prefix.
    mism = _prefix_mismatches(rows)
    total = _total_rows(rows)
    A(f"Rows whose state is OUTSIDE the allowed set for its pincode prefix: "
      f"{len(mism)} ({len(mism) / total * 100:.2f}% of rows).")
    A("")
    if mism:
        by_prefix = defaultdict(int)
        for m in mism:
            by_prefix[m["pincode"][:3]] += 1
        A("Mismatch counts by 3-digit prefix (top 15):")
        A("")
        A("| prefix | count |")
        A("| :--- | ---: |")
        for pref, cnt in sorted(by_prefix.items(), key=lambda kv: -kv[1])[:15]:
            A(f"| {pref} | {cnt} |")
        A("")
        A("20 sample prefix mismatches:")
        A("")
        A("| pincode | state | allowed_states |")
        A("| :--- | :--- | :--- |")
        for m in mism[:20]:
            A(f"| {m['pincode']} | {m['state']} | {m['expected']} |")
        A("")


# First two digits of a pincode -> the postal circle/region's dominant state(s).
# This is a coarse sanity check only (report-only), not an authoritative map.
def _load_prefix_map():
    with open(os.path.join(config.MAPPINGS_DIR, "pin_prefix_states.json"), encoding="utf-8") as f:
        m = json.load(f)
    two = {k: set(v["states"]) for k, v in m["two_digit"].items()}
    three = {k: set(v["states"]) for k, v in m["three_digit"].items()}
    return two, three


def _prefix_mismatches(rows):
    """Report-only: rows whose state is outside the allowed set for its pincode
    prefix. 3-digit overrides take precedence over 2-digit; prefixes absent from
    the map are skipped."""
    two, three = _load_prefix_map()
    out = []
    for r in rows:
        if not r["state_name"]:
            continue
        pin = r["pincode"]
        allowed = three.get(pin[:3])
        if allowed is None:
            allowed = two.get(pin[:2])
        if allowed and r["state_name"] not in allowed:
            out.append({"pincode": pin, "state": r["state_name"], "expected": sorted(allowed)})
    return out
