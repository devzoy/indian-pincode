"""Output writers: canonical JSONL, metadata.json, and the human-readable REPORT.md."""

from __future__ import annotations

import json
import os
import statistics
from collections import defaultdict
from typing import Dict, List, Optional

from . import config
from .coordinates import haversine_km


def write_normalized(rows: List[Dict], centroids: Dict, path: str = config.NORMALIZED_PATH) -> None:
    """Write the canonical dataset as gzipped JSONL (one object per line).

    Gzip keeps this source-of-truth file small enough to commit (~3.5 MB vs ~64 MB
    raw) while remaining diff-friendly line-by-line after decompression.
    """
    import gzip

    os.makedirs(os.path.dirname(path), exist_ok=True)
    fields = [
        "pincode", "office_name", "office_type", "delivery_status",
        "division_name", "region_name", "circle_name", "district",
        "state_name", "state_source", "latitude", "longitude",
        "geo_quality", "geo_fixed",
    ]
    # mtime=0 for reproducible gzip output (byte-stable across runs of same data).
    with gzip.GzipFile(path, "wb", mtime=0) as gz:
        for row in rows:
            out = {k: row.get(k) for k in fields}
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
        "source": {
            "resource_id": config.RESOURCE_ID,
            "sha256": fetch_result.sha256 if fetch_result else None,
            "fetched_at": fetch_result.fetched_at if fetch_result else None,
            "origin": fetch_result.source if fetch_result else "local",
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
    A(f"- **source_updated_date:** `{meta['source_updated_date']}`")
    A(f"- **source origin:** `{meta['source']['origin']}`  ")
    A(f"- **source SHA-256:** `{meta['source']['sha256']}`")
    A(f"- **fetched_at:** `{meta['source']['fetched_at']}`")
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
    else:
        A("| Metric | shipped | fresh | delta |")
        A("| :--- | ---: | ---: | ---: |")
        for k, label in [("pincode_count", "Unique pincodes"),
                         ("post_office_count", "Post office rows")]:
            old = fresh_diff["shipped"].get(k)
            new = fresh_diff["fresh"].get(k)
            delta = (new - old) if (old is not None and new is not None) else "n/a"
            A(f"| {label} | {old} | {new} | {delta} |")
        A("")
        A(f"Pincodes added: {fresh_diff['pincodes_added']}; removed: {fresh_diff['pincodes_removed']}.")
    A("")

    # Sanity gates
    A("## Sanity gates")
    A("")
    A("| Gate | Result | Detail |")
    A("| :--- | :--- | :--- |")
    for g in meta["gates"]["results"]:
        A(f"| {g['gate']} | {'PASS' if g['ok'] else 'FAIL'} | {g['detail']} |")
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
        A(f"**Sibling-distance distribution** (each office vs the median of its "
          f"same-pincode siblings; n={dd['n']}). Current flag threshold: "
          f"**{dd['threshold_km']} km**.")
        A("")
        A("| percentile | distance (km) |")
        A("| :--- | ---: |")
        for k in ["p50", "p75", "p90", "p95", "p99"]:
            A(f"| {k} | {dd[k]} |")
        A(f"| max | {dd['max']} |")
        A("")
        A("| threshold | rows exceeding | % of evaluated |")
        A("| :--- | ---: | ---: |")
        for t in ["25", "50", "75", "100", "150", "200"]:
            c = dd["over_km"][t]
            A(f"| > {t} km | {c} | {c / dd['n'] * 100:.2f}% |")
        A("")
        A("> Interpretation: the median office sits ~"
          f"{dd['p50']} km from its pincode siblings and p75 is ~{dd['p75']} km, so "
          "there is a clear knee well below 50 km. Points beyond ~100 km "
          f"({dd['over_km']['100']} rows) are almost certainly bad coordinates; the "
          "50–100 km band is ambiguous (some genuinely large rural pincodes). "
          "Suspects are flagged, not deleted: findNearby excludes them by default but "
          "`includeSuspect` recovers them, and pincode centroids ignore them.")
        A("")
    # Distance distribution across sampled + we approximate using all suspects'
    # distances captured in samples; the full distribution requires re-derivation,
    # so we bucket the sampled distances.
    if samples:
        dists = sorted(s["distance_km"] for s in samples if s["distance_km"] is not None)
        if dists:
            A(f"Sampled flagged-distance range: {dists[0]}–{dists[-1]} km "
              f"(median {statistics.median(dists):.1f} km).")
            A("")
        A("20 random flagged rows (deterministic sample):")
        A("")
        A("| pincode | office | state | district | lat | lon | rule | dist_km |")
        A("| :--- | :--- | :--- | :--- | ---: | ---: | :--- | ---: |")
        for s in samples:
            A(f"| {s['pincode']} | {s['office_name']} | {s['state_name']} | "
              f"{s['district']} | {s['latitude']} | {s['longitude']} | {s['reason']} | "
              f"{s['distance_km']} |")
        A("")
    else:
        A("No rows were flagged as suspect.")
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

    # prefix mismatch: state doesn't match the pincode's 2-digit postal prefix.
    mism = _prefix_mismatches(rows)
    A(f"Rows whose state disagrees with the pincode's 2-digit postal prefix: {len(mism)}.")
    A("")
    if mism:
        A("Sample prefix mismatches:")
        A("")
        A("| pincode | state | expected_region_states |")
        A("| :--- | :--- | :--- |")
        for m in mism[:20]:
            A(f"| {m['pincode']} | {m['state']} | {m['expected']} |")
        A("")


# First two digits of a pincode -> the postal circle/region's dominant state(s).
# This is a coarse sanity check only (report-only), not an authoritative map.
_PREFIX_STATES = {
    "11": {"DELHI"},
    "12": {"HARYANA"}, "13": {"HARYANA", "PUNJAB"},
    "14": {"PUNJAB"}, "15": {"PUNJAB"}, "16": {"PUNJAB", "CHANDIGARH"},
    "17": {"HIMACHAL PRADESH"}, "18": {"JAMMU AND KASHMIR", "LADAKH"},
    "19": {"JAMMU AND KASHMIR", "LADAKH"},
    "20": {"UTTAR PRADESH"}, "21": {"UTTAR PRADESH"}, "22": {"UTTAR PRADESH"},
    "23": {"UTTAR PRADESH"}, "24": {"UTTAR PRADESH"}, "25": {"UTTAR PRADESH"},
    "26": {"UTTAR PRADESH"}, "27": {"UTTAR PRADESH"}, "28": {"UTTAR PRADESH"},
    "30": {"RAJASTHAN"}, "31": {"RAJASTHAN"}, "32": {"RAJASTHAN"},
    "33": {"RAJASTHAN"}, "34": {"RAJASTHAN"},
    "36": {"GUJARAT"}, "37": {"GUJARAT"}, "38": {"GUJARAT"}, "39": {"GUJARAT"},
    "40": {"MAHARASHTRA"}, "41": {"MAHARASHTRA"}, "42": {"MAHARASHTRA"},
    "43": {"MAHARASHTRA"}, "44": {"MAHARASHTRA"},
    "45": {"MADHYA PRADESH"}, "46": {"MADHYA PRADESH"}, "47": {"MADHYA PRADESH"},
    "48": {"MADHYA PRADESH"}, "49": {"CHHATTISGARH"},
    "50": {"TELANGANA"}, "51": {"ANDHRA PRADESH", "TELANGANA"},
    "52": {"ANDHRA PRADESH"}, "53": {"ANDHRA PRADESH"},
    "56": {"KARNATAKA"}, "57": {"KARNATAKA"}, "58": {"KARNATAKA"}, "59": {"KARNATAKA"},
    "60": {"TAMIL NADU"}, "61": {"TAMIL NADU"}, "62": {"TAMIL NADU"},
    "63": {"TAMIL NADU"}, "64": {"TAMIL NADU"},
    "67": {"KERALA"}, "68": {"KERALA"}, "69": {"KERALA"},
    "682": {"LAKSHADWEEP"},
    "70": {"WEST BENGAL"}, "71": {"WEST BENGAL"}, "72": {"WEST BENGAL"},
    "73": {"WEST BENGAL"},
    "74": {"WEST BENGAL", "ANDAMAN AND NICOBAR ISLANDS", "SIKKIM"},
    "75": {"ODISHA"}, "76": {"ODISHA"}, "77": {"ODISHA"},
    "78": {"ASSAM"}, "79": {"ARUNACHAL PRADESH", "MANIPUR", "MIZORAM",
                            "NAGALAND", "TRIPURA", "MEGHALAYA"},
    "80": {"BIHAR"}, "81": {"BIHAR"}, "82": {"BIHAR"}, "83": {"JHARKHAND"},
    "84": {"BIHAR"}, "85": {"BIHAR"},
}


def _prefix_mismatches(rows):
    out = []
    for r in rows:
        if not r["state_name"]:
            continue
        pin = r["pincode"]
        expected = _PREFIX_STATES.get(pin[:3]) or _PREFIX_STATES.get(pin[:2])
        if expected and r["state_name"] not in expected:
            out.append({"pincode": pin, "state": r["state_name"], "expected": sorted(expected)})
    return out
