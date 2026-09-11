"""Normalization step: schema gate, field cleanup, state/district canonicalization,
NA-state backfill, office-type/delivery enums, and exact-duplicate removal.

Produces a list of normalized row dicts (coordinates handled separately in
pipeline.coordinates) plus a stats dict for the report.
"""

from __future__ import annotations

import json
import os
import re
from collections import Counter, defaultdict
from typing import Dict, List, Tuple

from . import config

PIN_RE = re.compile(r"^[1-9][0-9]{5}$")
_WS_RE = re.compile(r"\s+")

# Multi-state circles that must never be used to infer state.
_EXCLUDED_CIRCLES = None
_SINGLE_STATE_CIRCLES = None
_STATE_ALIASES = None
_STATE_CANONICAL = None
_DISTRICT_ALIASES = None


def _load_mappings():
    global _EXCLUDED_CIRCLES, _SINGLE_STATE_CIRCLES, _STATE_ALIASES
    global _STATE_CANONICAL, _DISTRICT_ALIASES
    if _STATE_CANONICAL is not None:
        return
    with open(os.path.join(config.MAPPINGS_DIR, "states.json"), encoding="utf-8") as f:
        s = json.load(f)
    _STATE_CANONICAL = set(s["canonical"])
    _STATE_ALIASES = {_norm_key(k): v for k, v in s["aliases"].items()}
    with open(os.path.join(config.MAPPINGS_DIR, "circles.json"), encoding="utf-8") as f:
        c = json.load(f)
    _SINGLE_STATE_CIRCLES = {_norm_key(k): v for k, v in c["single_state_circles"].items()}
    _EXCLUDED_CIRCLES = {_norm_key(x) for x in c["excluded_multi_state_circles"]}
    with open(os.path.join(config.MAPPINGS_DIR, "districts.json"), encoding="utf-8") as f:
        d = json.load(f)
    _DISTRICT_ALIASES = {_norm_key(k): v for k, v in d["aliases"].items()}


def _clean_ws(value) -> str:
    if value is None:
        return ""
    return _WS_RE.sub(" ", str(value)).strip()


def _norm_key(value) -> str:
    return _clean_ws(value).upper()


def _is_na(value: str) -> bool:
    return value == "" or value.upper() == "NA"


def canonical_state(raw_state: str) -> Tuple[str, bool]:
    """Return (canonical_state_or_empty, is_known). Empty string means NA/unknown."""
    _load_mappings()
    key = _norm_key(raw_state)
    if _is_na(key):
        return "", False
    if key in _STATE_ALIASES:
        return _STATE_ALIASES[key], True
    if key in _STATE_CANONICAL:
        return key, True
    # Unknown but non-NA: keep as-is (uppercased) and flag as not-known so the
    # report can surface it, but do not drop.
    return key, False


def canonical_district(raw_district: str) -> str:
    _load_mappings()
    key = _norm_key(raw_district)
    if _is_na(key):
        return ""
    return _DISTRICT_ALIASES.get(key, key)


def normalize(rows: List[Dict[str, str]]) -> Tuple[List[Dict], Dict]:
    """Normalize all rows. Coordinates are passed through as raw strings here
    (lat_raw/lon_raw) and cleaned in pipeline.coordinates."""
    _load_mappings()
    _schema_gate(rows)

    stats = {
        "input_rows": len(rows),
        "invalid_pincode_dropped": 0,
        "exact_duplicates_removed": 0,
        "unknown_office_type": Counter(),
        "unknown_delivery": Counter(),
        "unknown_state_kept": Counter(),
        "state_source": Counter(),
        "na_backfill": {"inferred_pincode": 0, "inferred_circle": 0, "null": 0},
    }

    # First pass: clean fields, drop invalid pincodes.
    cleaned: List[Dict] = []
    for r in rows:
        pin = _clean_ws(r.get("pincode"))
        if not PIN_RE.match(pin):
            stats["invalid_pincode_dropped"] += 1
            continue

        office = _clean_ws(r.get("officename"))
        otype_raw = _norm_key(r.get("officetype"))
        otype = otype_raw if otype_raw in config.OFFICE_TYPES else otype_raw
        if otype_raw and otype_raw not in config.OFFICE_TYPES:
            stats["unknown_office_type"][otype_raw] += 1

        delivery_raw = _clean_ws(r.get("delivery"))
        # Canonicalize delivery capitalization to the fixed enum.
        delivery = _canon_delivery(delivery_raw)
        if delivery not in config.DELIVERY_STATUSES:
            stats["unknown_delivery"][delivery_raw] += 1

        state, state_known = canonical_state(r.get("statename"))
        if state and not state_known:
            stats["unknown_state_kept"][state] += 1
        district = canonical_district(r.get("district"))

        cleaned.append({
            "pincode": pin,
            "office_name": office,
            "office_type": otype,
            "delivery_status": delivery,
            "division_name": _clean_ws(r.get("divisionname")),
            "region_name": _clean_ws(r.get("regionname")),
            "circle_name": _clean_ws(r.get("circlename")),
            "district": district,
            "state_name": state,           # may be "" (NA); backfilled below
            "state_source": "source" if state else "",
            "lat_raw": _clean_ws(r.get("latitude")),
            "lon_raw": _clean_ws(r.get("longitude")),
        })

    # Backfill NA states.
    _backfill_states(cleaned, stats)

    # Dedupe exact duplicates (on the normalized identity, incl raw coords).
    deduped, dupes = _dedupe(cleaned)
    stats["exact_duplicates_removed"] = dupes

    for row in deduped:
        stats["state_source"][row["state_source"] or "null"] += 1

    stats["output_rows"] = len(deduped)
    # Convert Counters to plain dicts for JSON.
    stats["unknown_office_type"] = dict(stats["unknown_office_type"])
    stats["unknown_delivery"] = dict(stats["unknown_delivery"])
    stats["unknown_state_kept"] = dict(stats["unknown_state_kept"])
    stats["state_source"] = dict(stats["state_source"])
    return deduped, stats


def _canon_delivery(value: str) -> str:
    v = value.strip().lower()
    if v in ("delivery",):
        return "Delivery"
    if v in ("non delivery", "non-delivery", "nondelivery"):
        return "Non Delivery"
    return value  # unknown; report will flag


def _schema_gate(rows: List[Dict[str, str]]) -> None:
    if not rows:
        raise RuntimeError("schema gate: input has zero rows")
    present = set(rows[0].keys())
    missing = [c for c in config.EXPECTED_COLUMNS if c not in present]
    if missing:
        raise RuntimeError(
            f"schema gate failed: missing columns {missing}; present={sorted(present)}"
        )


def _backfill_states(cleaned: List[Dict], stats: Dict) -> None:
    _load_mappings()
    # Build pincode -> set of known states (source rows only).
    pin_states: Dict[str, set] = defaultdict(set)
    for row in cleaned:
        if row["state_name"]:
            pin_states[row["pincode"]].add(row["state_name"])

    for row in cleaned:
        if row["state_name"]:
            continue  # already has a source state
        # (a) same-pincode siblings, if they unanimously agree.
        sib = pin_states.get(row["pincode"])
        if sib and len(sib) == 1:
            row["state_name"] = next(iter(sib))
            row["state_source"] = "inferred_pincode"
            stats["na_backfill"]["inferred_pincode"] += 1
            continue
        # (b) circle, only if single-state (and not excluded).
        ckey = _norm_key(row["circle_name"])
        if ckey in _SINGLE_STATE_CIRCLES and ckey not in _EXCLUDED_CIRCLES:
            row["state_name"] = _SINGLE_STATE_CIRCLES[ckey]
            row["state_source"] = "inferred_circle"
            stats["na_backfill"]["inferred_circle"] += 1
            continue
        # (c) null.
        row["state_name"] = None
        row["state_source"] = "null"
        stats["na_backfill"]["null"] += 1


def _dedupe(cleaned: List[Dict]) -> Tuple[List[Dict], int]:
    seen = set()
    out = []
    dupes = 0
    for row in cleaned:
        key = (
            row["pincode"], row["office_name"], row["office_type"],
            row["delivery_status"], row["division_name"], row["region_name"],
            row["circle_name"], row["district"], row["state_name"],
            row["lat_raw"], row["lon_raw"],
        )
        if key in seen:
            dupes += 1
            continue
        seen.add(key)
        out.append(row)
    return out, dupes
