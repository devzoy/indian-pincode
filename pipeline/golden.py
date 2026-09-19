"""Generate tests/fixtures/golden.json from the canonical normalized dataset.

The fixture is the parity guarantee: both the Python and Node test suites assert
against this same file (after mapping key casing). It samples >=200 pincodes
covering every state/UT, multi-district pincodes, ALL cross-state pincodes, the
UT islands, the North-East, and pincodes whose coordinates were swapped, flagged
suspect, removed, or are missing.

Values are stored in a NEUTRAL (snake_case) form. Each language's test maps to
its own casing.

Invoked by: python -m pipeline.build --emit-golden
"""

from __future__ import annotations

import gzip
import json
import os
import random
from collections import defaultdict
from typing import Dict, List

from . import config

GOLDEN_PATH = os.path.join(config.REPO_ROOT, "tests", "fixtures", "golden.json")

_NE_STATES = {
    "ARUNACHAL PRADESH", "MANIPUR", "MEGHALAYA", "MIZORAM",
    "NAGALAND", "TRIPURA", "ASSAM", "SIKKIM",
}
_ISLAND_STATES = {"ANDAMAN AND NICOBAR ISLANDS", "LAKSHADWEEP"}


def _load_rows() -> List[Dict]:
    rows = []
    with gzip.open(config.NORMALIZED_PATH, "rt", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _primary_state(rows_for_pin):
    counts = defaultdict(int)
    for r in rows_for_pin:
        if r["state_name"]:
            counts[r["state_name"]] += 1
    if not counts:
        return None
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


def _core_expected(pin, rows_for_pin) -> Dict:
    states = sorted({r["state_name"] for r in rows_for_pin if r["state_name"]})
    # (state, district) pairs -> district names (all), state_source of primary
    districts = sorted({r["district"] for r in rows_for_pin if r["district"]})
    primary = _primary_state(rows_for_pin)
    state_source = "null"
    if primary:
        # source wins over inferred for the primary state
        srcs = [r["state_source"] for r in rows_for_pin if r["state_name"] == primary]
        state_source = "source" if "source" in srcs else (srcs[0] if srcs else "null")
    return {
        "pincode": pin,
        "state": primary,
        "states": states,
        "state_source": state_source,
        "districts": districts,
    }


def _geo_office(r) -> Dict:
    return {
        "pincode": r["pincode"],
        "office_name": r["office_name"],
        "office_type": r["office_type"],
        "delivery_status": r["delivery_status"],
        "district": r["district"] or None,
        "state": r["state_name"] or None,
        "state_source": r["state_source"] or "null",
        "latitude": r["latitude"],
        "longitude": r["longitude"],
        "geo_quality": r["geo_quality"],
    }


_TYPE_ORDER = {"HO": 0, "PO": 1, "BO": 2}


def _geo_expected(pin, rows_for_pin) -> List[Dict]:
    offices = [_geo_office(r) for r in rows_for_pin]
    offices.sort(key=lambda o: (_TYPE_ORDER.get(o["office_type"], 9), o["office_name"]))
    return offices


def build_golden(seed: int = 20251003) -> Dict:
    rows = _load_rows()
    by_pin: Dict[str, List[Dict]] = defaultdict(list)
    for r in rows:
        by_pin[r["pincode"]].append(r)

    pin_states = {p: {r["state_name"] for r in rs if r["state_name"]} for p, rs in by_pin.items()}
    pin_districts = {p: {r["district"] for r in rs if r["district"]} for p, rs in by_pin.items()}
    pin_gq = {p: {r["geo_quality"] for r in rs} for p, rs in by_pin.items()}
    pin_primary = {p: _primary_state(rs) for p, rs in by_pin.items()}

    selected = set()

    def add(pins):
        for p in pins:
            if p in by_pin:
                selected.add(p)

    # 1. ALL cross-state pincodes (states span > 1).
    cross_state = sorted(p for p, s in pin_states.items() if len(s) > 1)
    add(cross_state)

    # 2. At least a few pincodes per state/UT (primary state coverage).
    per_state = defaultdict(list)
    for p, st in pin_primary.items():
        if st:
            per_state[st].append(p)
    rng = random.Random(seed)
    for st, pins in per_state.items():
        pins_sorted = sorted(pins)
        rng.shuffle(pins_sorted)
        add(pins_sorted[:4])   # >=4 per state/UT

    # 3. Islands + North-East explicit anchors.
    add(["744101", "682555"])
    for p, st in pin_primary.items():
        if st in _ISLAND_STATES or st in _NE_STATES:
            selected.add(p)
            if len([x for x in selected if pin_primary.get(x) == st]) >= 6:
                pass

    # 4. Multi-district pincodes.
    multi_d = sorted(p for p, d in pin_districts.items() if len(d) > 1)
    rng.shuffle(multi_d)
    add(multi_d[:30])

    # 5. Each geo_quality class (swapped/suspect/removed/missing/original).
    for quality in ("swapped", "suspect", "removed", "missing", "original"):
        pins_q = sorted(p for p, qs in pin_gq.items() if quality in qs)
        rng.shuffle(pins_q)
        add(pins_q[:8])

    # Ensure >= 200.
    if len(selected) < 200:
        extra = sorted(set(by_pin) - selected)
        rng.shuffle(extra)
        add(extra[: 200 - len(selected)])

    entries = []
    for pin in sorted(selected):
        rows_for_pin = by_pin[pin]
        entries.append({
            "pincode": pin,
            "core": _core_expected(pin, rows_for_pin),
            "geo": _geo_expected(pin, rows_for_pin),
        })

    return {
        "_comment": "Generated by `python -m pipeline.build --emit-golden`. Neutral "
                    "snake_case values; each language's test maps key casing. Both "
                    "Python and Node assert against THIS file (parity guarantee).",
        "data_version": _data_version(),
        "count": len(entries),
        "entries": entries,
    }


def _data_version():
    with open(config.METADATA_PATH, encoding="utf-8") as f:
        return json.load(f)["data_version"]


def emit_golden() -> Dict:
    golden = build_golden()
    os.makedirs(os.path.dirname(GOLDEN_PATH), exist_ok=True)
    with open(GOLDEN_PATH, "w", encoding="utf-8") as f:
        json.dump(golden, f, ensure_ascii=False, indent=1, sort_keys=True)
    # stats for the caller
    states = set()
    for e in golden["entries"]:
        if e["core"]["state"]:
            states.add(e["core"]["state"])
    print(f"[golden] wrote {GOLDEN_PATH}: {golden['count']} pincodes, "
          f"{len(states)} states/UTs covered")
    return golden
