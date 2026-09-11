"""Build orchestrator. Run with: python -m pipeline.build [options]

Steps: fetch (optional) -> normalize -> clean coordinates -> sanity gates ->
write canonical outputs, metadata, and REPORT.md.

No network access occurs unless --fetch is passed AND DATA_GOV_IN_API_KEY is set.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, Optional

from . import config, fetch, normalize, coordinates, gates, outputs


def _load_previous_metadata() -> Optional[Dict]:
    """Load the previous build's counts for the sanity-gate diff. Falls back to
    the recorded v1.0.4 baseline when no prior metadata.json exists."""
    if os.path.exists(config.METADATA_PATH):
        try:
            with open(config.METADATA_PATH, encoding="utf-8") as f:
                prev = json.load(f)
            return prev.get("counts")
        except (json.JSONDecodeError, KeyError):
            pass
    return {
        "pincode_count": config.V1_BASELINE["pincode_count"],
        "post_office_count": config.V1_BASELINE["post_office_count"],
    }


def run(cfg: config.Config) -> Dict:
    # 1. Fetch (or None -> use local CSV).
    fr = fetch.fetch(cfg)
    fresh_fetch_result = fr  # may be None
    if fr is None:
        print(f"[build] using local CSV: {cfg.local_csv}")
        fr = fetch.from_local(cfg.local_csv)

    # 2. Source date policy. API fetch supplies source_updated_date; local mode
    #    must obtain it from --source-date or a prior metadata.json, else fail.
    source_updated_date = fr.source_updated_date
    if source_updated_date is None:
        source_updated_date = _local_source_date_or_fail(cfg)

    # 3. Normalize.
    rows, norm_stats = normalize.normalize(fr.rows)

    # 4. Coordinates.
    rows, coord_result = coordinates.clean(rows, cfg.thresholds)
    coord_stats = coord_result["stats"]
    centroids = coord_result["centroids"]

    # 5. Sanity gates.
    previous = _load_previous_metadata()
    gate_result = gates.evaluate(rows, cfg.thresholds, previous)
    print(f"[build] gates: {'PASS' if gate_result['ok'] else 'FAIL'}")
    for g in gate_result["results"]:
        print(f"    [{'ok' if g['ok'] else 'FAIL'}] {g['gate']}: {g['detail']}")
    if not gate_result["ok"] and cfg.enforce_gates:
        _write_report_only(rows, fr, norm_stats, coord_result, gate_result,
                           source_updated_date, previous, fresh_fetch_result, cfg)
        raise SystemExit("[build] sanity gates failed; see data/REPORT.md")

    # 6. Metadata + outputs.
    meta = outputs.build_metadata(
        rows, fr, norm_stats,
        {**coord_stats},  # coordinate_stats excludes flagged_samples inside build_metadata
        gate_result, source_updated_date,
    )
    outputs.write_normalized(rows, centroids)
    outputs.write_metadata(meta)

    v1_diff = _v1_reproduction_diff(rows, previous)
    fresh_diff = _fresh_diff(rows, fresh_fetch_result)
    outputs.write_report(rows, meta, norm_stats, coord_result, v1_diff, fresh_diff)

    print(f"[build] wrote {config.NORMALIZED_PATH}")
    print(f"[build] wrote {config.METADATA_PATH}")
    print(f"[build] wrote {config.REPORT_PATH}")
    return {"meta": meta, "gate_result": gate_result}


def _local_source_date_or_fail(cfg: config.Config) -> str:
    # For a local build: prefer an explicit --source-date, then a prior
    # metadata.json's source_updated_date. Otherwise FAIL per policy (never fall
    # back to the fetch time).
    if cfg.local_source_date:
        return cfg.local_source_date
    if os.path.exists(config.METADATA_PATH):
        try:
            with open(config.METADATA_PATH, encoding="utf-8") as f:
                prev = json.load(f)
            if prev.get("source_updated_date"):
                return prev["source_updated_date"]
        except (json.JSONDecodeError, KeyError):
            pass
    raise SystemExit(
        "[build] source_updated_date is unknown for a local build. "
        "Pass --source-date DD/MM/YYYY (from the data.gov.in resource's API "
        "updated_date), or run with --fetch and DATA_GOV_IN_API_KEY set. "
        "Per policy the pipeline never falls back to the fetch time."
    )


def _v1_reproduction_diff(rows, previous) -> Dict:
    pincodes = set(r["pincode"] for r in rows)
    current = {"pincode_count": len(pincodes), "post_office_count": len(rows)}
    # The reproduction diff always compares against the fixed v1.0.4 baseline
    # counts (from the Phase 0 audit), never against a prior build.
    v1 = {
        "pincode_count": config.V1_BASELINE["pincode_count"],
        "post_office_count": config.V1_BASELINE["post_office_count"],
    }
    # Reconstruct the v1.0.4 pincode set from the shipped validation index
    # (pincodes.compressed.json: prefix -> [suffix,...]) for a real set diff.
    v1_pins = _v1_pincode_set()
    if v1_pins is not None:
        added = len(pincodes - v1_pins)
        removed = len(v1_pins - pincodes)
    else:
        added, removed = "n/a", "n/a"
    return {
        "previous": v1,
        "current": current,
        "pincodes_added": added,
        "pincodes_removed": removed,
    }


def _v1_pincode_set():
    """Reconstruct the v1.0.4 pincode set from the shipped compressed index."""
    idx_path = os.path.join(
        config.REPO_ROOT, "src", "node", "data", "pincodes.compressed.json"
    )
    if not os.path.exists(idx_path):
        return None
    try:
        with open(idx_path, encoding="utf-8") as f:
            idx = json.load(f)
    except json.JSONDecodeError:
        return None
    pins = set()
    for prefix, suffixes in idx.items():
        for suf in suffixes:
            pins.add(f"{prefix}{int(suf):03d}")
    return pins


def _fresh_diff(rows, fresh_fetch_result) -> Optional[Dict]:
    if fresh_fetch_result is None:
        return None
    # The `rows` already reflect the fresh fetch (since fetch happened). Compare
    # against the currently-shipped normalized file if present.
    fresh_pins = set(r["pincode"] for r in rows)
    fresh = {"pincode_count": len(fresh_pins), "post_office_count": len(rows)}
    shipped = {"pincode_count": config.V1_BASELINE["pincode_count"],
               "post_office_count": config.V1_BASELINE["post_office_count"]}
    return {
        "shipped": shipped,
        "fresh": fresh,
        "pincodes_added": "n/a (no shipped set)",
        "pincodes_removed": "n/a",
    }


def _write_report_only(rows, fr, norm_stats, coord_result, gate_result,
                       source_updated_date, previous, fresh_fetch_result, cfg):
    meta = outputs.build_metadata(
        rows, fr, norm_stats, {**coord_result["stats"]},
        gate_result, source_updated_date,
    )
    v1_diff = _v1_reproduction_diff(rows, previous)
    fresh_diff = _fresh_diff(rows, fresh_fetch_result)
    outputs.write_report(rows, meta, norm_stats, coord_result, v1_diff, fresh_diff)


def main(argv=None):
    p = argparse.ArgumentParser(description="Build the canonical indian-pincode dataset.")
    p.add_argument("--fetch", action="store_true",
                   help="fetch from data.gov.in API (needs DATA_GOV_IN_API_KEY)")
    p.add_argument("--local-csv", default=config.DEFAULT_LOCAL_CSV,
                   help="path to a local raw CSV (default: data/raw-data.csv)")
    p.add_argument("--source-date", default=None,
                   help="DD/MM/YYYY source updated_date for local builds "
                        "(required if unknown and no prior metadata)")
    p.add_argument("--no-enforce-gates", action="store_true",
                   help="warn instead of failing on sanity-gate violations")
    # threshold overrides
    p.add_argument("--sibling-flag-km", type=float, default=None)
    p.add_argument("--district-hard-km", type=float, default=None)
    args = p.parse_args(argv)

    cfg = config.Config(
        local_csv=args.local_csv,
        do_fetch=args.fetch,
        enforce_gates=not args.no_enforce_gates,
    )
    if args.sibling_flag_km is not None:
        cfg.thresholds.sibling_flag_km = args.sibling_flag_km
    if args.district_hard_km is not None:
        cfg.thresholds.district_hard_km = args.district_hard_km

    # Allow supplying source date for local builds via CLI (explicit DD/MM/YYYY).
    if args.source_date:
        cfg.local_source_date = fetch.parse_source_updated_date(args.source_date)

    run(cfg)


if __name__ == "__main__":
    main()
