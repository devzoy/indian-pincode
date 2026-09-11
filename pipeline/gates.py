"""Sanity gates. The build fails (when enforced) if any gate is violated:
  * pincode count differs from previous release by more than gate_pincode_pct
  * post office count differs by more than gate_post_office_pct
  * any state/UT has zero pincodes
  * more than gate_max_null_coord_pct of rows end up with null coordinates
Thresholds are configurable via config.Thresholds.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional

from . import config


def evaluate(
    rows: List[Dict],
    th: config.Thresholds,
    previous: Optional[Dict],
) -> Dict:
    pincodes = set(r["pincode"] for r in rows)
    pincode_count = len(pincodes)
    post_office_count = len(rows)

    null_coord = sum(1 for r in rows if r["latitude"] is None)
    null_coord_pct = null_coord / post_office_count if post_office_count else 0.0

    # states with at least one pincode (ignore null states for the zero check,
    # but every canonical state present must have >=1 pincode; a state with zero
    # would simply be absent, so we check against the expected canonical set).
    state_pins: Dict[str, set] = defaultdict(set)
    for r in rows:
        if r["state_name"]:
            state_pins[r["state_name"]].add(r["pincode"])

    prev_pin = (previous or {}).get("pincode_count")
    prev_po = (previous or {}).get("post_office_count")

    results = []

    def check(name, ok, detail):
        results.append({"gate": name, "ok": bool(ok), "detail": detail})

    # pincode count diff
    if prev_pin:
        diff = abs(pincode_count - prev_pin) / prev_pin
        check(
            "pincode_count_within_pct",
            diff <= th.gate_pincode_pct,
            f"current={pincode_count} previous={prev_pin} diff={diff:.4f} "
            f"limit={th.gate_pincode_pct}",
        )
    else:
        check("pincode_count_within_pct", True, "no previous baseline; skipped")

    # post office count diff
    if prev_po:
        diff = abs(post_office_count - prev_po) / prev_po
        check(
            "post_office_count_within_pct",
            diff <= th.gate_post_office_pct,
            f"current={post_office_count} previous={prev_po} diff={diff:.4f} "
            f"limit={th.gate_post_office_pct}",
        )
    else:
        check("post_office_count_within_pct", True, "no previous baseline; skipped")

    # every canonical state present
    with open_states() as canonical:
        missing_states = sorted(s for s in canonical if s not in state_pins)
    check(
        "all_states_have_pincodes",
        len(missing_states) == 0,
        f"missing={missing_states}" if missing_states else "all canonical states present",
    )

    # null coord pct
    check(
        "null_coord_pct_under_limit",
        null_coord_pct <= th.gate_max_null_coord_pct,
        f"null_coord={null_coord} pct={null_coord_pct:.4f} limit={th.gate_max_null_coord_pct}",
    )

    all_ok = all(r["ok"] for r in results)
    return {
        "ok": all_ok,
        "results": results,
        "pincode_count": pincode_count,
        "post_office_count": post_office_count,
        "null_coord": null_coord,
        "null_coord_pct": null_coord_pct,
    }


class open_states:
    """Context manager returning the canonical state set from mappings."""

    def __enter__(self):
        import json
        import os
        with open(os.path.join(config.MAPPINGS_DIR, "states.json"), encoding="utf-8") as f:
            return set(json.load(f)["canonical"])

    def __exit__(self, *a):
        return False
