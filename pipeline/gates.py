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
    accept_baseline_change: Optional[str] = None,
) -> Dict:
    """Evaluate sanity gates.

    If `accept_baseline_change` is a non-empty reason string, a FAILING *count*
    gate (pincode/post-office) is downgraded to a warning ONLY when the observed
    change is within +/-10%; the reason is attached. Changes beyond +/-10% still
    fail regardless (the caller/CLI is expected to STOP in that case)."""
    HARD_CAP = 0.10
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

    def check(name, ok, detail, warning=False):
        results.append({"gate": name, "ok": bool(ok), "detail": detail,
                        "warning": bool(warning)})

    def count_gate(name, current, prev, limit):
        if not prev:
            check(name, True, "no previous baseline; skipped")
            return
        diff = abs(current - prev) / prev
        ok = diff <= limit
        detail = f"current={current} previous={prev} diff={diff:.4f} limit={limit}"
        if not ok and accept_baseline_change and diff <= HARD_CAP:
            # Downgrade to a warning (still within +/-10%).
            check(name, True, detail + f" [WAIVED within {HARD_CAP:.0%}: "
                                       f"{accept_baseline_change}]", warning=True)
        else:
            check(name, ok, detail)

    count_gate("pincode_count_within_pct", pincode_count, prev_pin, th.gate_pincode_pct)
    count_gate("post_office_count_within_pct", post_office_count, prev_po, th.gate_post_office_pct)

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
        "baseline_change_waiver": accept_baseline_change,
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
