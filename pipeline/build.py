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
    import datetime as _dt
    _started_at = _dt.datetime.now(_dt.timezone.utc)

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
    gate_result = gates.evaluate(rows, cfg.thresholds, previous, cfg.accept_baseline_change)
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

    _write_build_log(fr, source_updated_date, _started_at, cfg)
    return {"meta": meta, "gate_result": gate_result}


def _write_build_log(fr, source_updated_date, started_at, cfg):
    """Write run-time (non-deterministic) build info to a gitignored log so the
    committed outputs stay byte-stable across runs.

    `source_origin` (api / local / manual_csv) is provenance and lives ONLY here,
    never in metadata.json, so the committed build stays byte-identical regardless
    of how the identical source bytes were obtained."""
    import datetime as _dt
    import platform
    import socket

    os.makedirs(config.RAW_DIR, exist_ok=True)
    finished = _dt.datetime.now(_dt.timezone.utc)
    # An API fetch always reports origin "api"; otherwise use the configured
    # source_origin ("manual_csv" for --from-csv, else "local").
    origin = fr.source if (fr and fr.source == "api") else cfg.source_origin
    log = {
        "started_at": started_at.isoformat(),
        "finished_at": finished.isoformat(),
        "duration_seconds": round((finished - started_at).total_seconds(), 3),
        "fetched_at": fr.fetched_at if fr else None,
        "source_origin": origin,
        "source_path": getattr(fr, "raw_path", None),
        "source_sha256": fr.sha256 if fr else None,
        "source_updated_date": source_updated_date,
        "host": socket.gethostname(),
        "platform": platform.platform(),
        "python": platform.python_version(),
    }
    path = os.path.join(config.RAW_DIR, "build_log.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)
    print(f"[build] wrote {path} (gitignored)")


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


def _fresh_diff(rows, fresh_fetch_result, seed: int = 42) -> Optional[Dict]:
    """Compare the fresh build against the previously-committed normalized build
    (loaded from git HEAD), reporting pincode/office/state/district changes."""
    if fresh_fetch_result is None:
        return None

    prev = _load_committed_normalized()  # {pincode: {"pos": int, "sd": {(state,district),...}}}
    if prev is None:
        # No committed baseline to diff against.
        fresh_pins = set(r["pincode"] for r in rows)
        return {
            "available": False,
            "fresh": {"pincode_count": len(fresh_pins), "post_office_count": len(rows)},
        }

    import random
    from collections import defaultdict

    fresh_pins = set(r["pincode"] for r in rows)
    fresh_sd = defaultdict(set)
    for r in rows:
        fresh_sd[r["pincode"]].add((r["state_name"], r["district"]))
    fresh_states = set(r["state_name"] for r in rows if r["state_name"])
    fresh_districts = set(r["district"] for r in rows if r["district"])

    prev_pins = set(prev["pins"])
    added = sorted(fresh_pins - prev_pins)
    removed = sorted(prev_pins - fresh_pins)

    # pincodes whose (state,district) set changed (present in both)
    changed_sd = []
    for p in fresh_pins & prev_pins:
        if fresh_sd[p] != prev["sd"].get(p, set()):
            changed_sd.append(p)

    rng = random.Random(seed)

    def _samp(items, k):
        return rng.sample(items, min(k, len(items))) if items else []

    return {
        "available": True,
        "previous": {"pincode_count": len(prev_pins), "post_office_count": prev["pos"]},
        "fresh": {"pincode_count": len(fresh_pins), "post_office_count": len(rows)},
        "pincodes_added": len(added),
        "pincodes_removed": len(removed),
        "pincodes_added_samples": _samp(added, 20),
        "pincodes_removed_samples": _samp(removed, 20),
        "post_offices_delta": len(rows) - prev["pos"],
        "pincodes_sd_changed": len(changed_sd),
        "pincodes_sd_changed_samples": _samp(changed_sd, 20),
        "new_states": sorted(fresh_states - prev["states"]),
        "removed_states": sorted(prev["states"] - fresh_states),
        "new_districts": sorted(fresh_districts - prev["districts"]),
        "removed_districts_count": len(prev["districts"] - fresh_districts),
    }


def _load_committed_normalized():
    """Load the previously-committed normalized build from git HEAD (before this
    run overwrites it), for the fresh-fetch diff. Returns None if unavailable."""
    import gzip
    import io
    import subprocess
    from collections import defaultdict

    rel = os.path.relpath(config.NORMALIZED_PATH, config.REPO_ROOT)
    try:
        blob = subprocess.run(
            ["git", "show", f"HEAD:{rel}"],
            cwd=config.REPO_ROOT, capture_output=True,
        )
        if blob.returncode != 0 or not blob.stdout:
            return None
        data = gzip.decompress(blob.stdout)
    except Exception:  # noqa: BLE001
        return None

    pins = set()
    sd = defaultdict(set)
    states = set()
    districts = set()
    pos = 0
    for line in io.BytesIO(data).read().decode("utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        pos += 1
        pins.add(rec["pincode"])
        sd[rec["pincode"]].add((rec.get("state_name"), rec.get("district")))
        if rec.get("state_name"):
            states.add(rec["state_name"])
        if rec.get("district"):
            districts.add(rec["district"])
    return {"pins": pins, "sd": sd, "states": states, "districts": districts, "pos": pos}


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
                   help="path to a local raw CSV/.gz (default: data/raw-data.csv.gz)")
    p.add_argument("--from-csv", default=None, metavar="PATH",
                   help="manual import: build from an externally-supplied CSV/.gz "
                        "through the same schema gate, normalization, and sanity "
                        "gates as the API path. Provenance is recorded as "
                        "'manual_csv' in build_log.json.")
    p.add_argument("--source-date", default=None,
                   help="DD/MM/YYYY source updated_date for local builds "
                        "(required if unknown and no prior metadata)")
    p.add_argument("--no-enforce-gates", action="store_true",
                   help="warn instead of failing on sanity-gate violations")
    p.add_argument("--page-size", type=int, default=5000,
                   help="API pagination page size (default 5000)")
    p.add_argument("--accept-baseline-change", default=None, metavar="REASON",
                   help="downgrade a failing count gate to a warning for this run "
                        "(only within +/-10%%); records REASON in metadata + report")
    p.add_argument("--emit-packages", action="store_true",
                   help="generate per-language package data from the canonical "
                        "normalized dataset (does not re-run the full build)")
    p.add_argument("--emit-golden", action="store_true",
                   help="generate tests/fixtures/golden.json from the canonical dataset")
    # threshold overrides (adaptive outlier rule)
    p.add_argument("--sibling-floor-km", type=float, default=None,
                   help="outlier floor: never flag a sibling-branch point below this")
    p.add_argument("--sibling-hard-km", type=float, default=None,
                   help="outlier hard cap: always flag beyond this distance")
    p.add_argument("--district-hard-km", type=float, default=None)
    args = p.parse_args(argv)

    if args.from_csv and args.fetch:
        raise SystemExit("[build] --from-csv and --fetch are mutually exclusive")

    cfg = config.Config(
        local_csv=args.from_csv or args.local_csv,
        do_fetch=args.fetch,
        enforce_gates=not args.no_enforce_gates,
        page_size=args.page_size,
        accept_baseline_change=args.accept_baseline_change,
        source_origin="manual_csv" if args.from_csv else "local",
    )
    if args.sibling_floor_km is not None:
        cfg.thresholds.sibling_floor_km = args.sibling_floor_km
    if args.sibling_hard_km is not None:
        cfg.thresholds.sibling_hard_km = args.sibling_hard_km
    if args.district_hard_km is not None:
        cfg.thresholds.district_hard_km = args.district_hard_km

    # Allow supplying source date for local builds via CLI (explicit DD/MM/YYYY).
    if args.source_date:
        cfg.local_source_date = fetch.parse_source_updated_date(args.source_date)

    # --emit-packages / --emit-golden run standalone against the existing build.
    if args.emit_packages or args.emit_golden:
        if not os.path.exists(config.NORMALIZED_PATH):
            raise SystemExit("[build] no canonical build found; run the full build first")
        if args.emit_packages:
            from . import emit
            emit.emit_all()
        if args.emit_golden:
            from . import golden
            golden.emit_golden()
        return

    run(cfg)


if __name__ == "__main__":
    main()
