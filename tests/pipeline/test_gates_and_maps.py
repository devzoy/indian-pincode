"""Pipeline: schema gate, sanity gates, --accept-baseline-change bounds, and the
prefix map (3-digit override precedence)."""

import json
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

from pipeline import normalize, gates, config, outputs  # noqa: E402


def _row(**kw):
    base = {
        "circlename": "Delhi Circle", "regionname": "R", "divisionname": "D",
        "officename": "X SO", "pincode": "110001", "officetype": "PO",
        "delivery": "Delivery", "district": "NEW DELHI", "statename": "DELHI",
        "latitude": "28.6", "longitude": "77.2",
    }
    base.update(kw)
    return base


# ---- schema gate ----

def test_schema_gate_fails_on_missing_column():
    rows = [{k: v for k, v in _row().items() if k != "latitude"}]
    with pytest.raises(RuntimeError, match="schema gate"):
        normalize.normalize(rows)


def test_schema_gate_passes_with_all_columns():
    rows = [_row(), _row(pincode="110002", officename="Y SO")]
    out, stats = normalize.normalize(rows)
    assert stats["output_rows"] == 2


# ---- sanity gates ----

def _norm_rows(state_pincodes):
    """Build minimal normalized rows: {state: [pincodes]}."""
    rows = []
    for state, pins in state_pincodes.items():
        for p in pins:
            rows.append({
                "pincode": p, "office_name": "O", "office_type": "PO",
                "delivery_status": "Delivery", "district": "D", "state_name": state,
                "state_source": "source", "latitude": 20.0, "longitude": 78.0,
                "geo_quality": "original",
            })
    return rows


def test_gate_pincode_count_fails_beyond_pct():
    th = config.Thresholds()
    rows = _norm_rows({"DELHI": [f"11000{i}" for i in range(1, 6)]})  # 5 pincodes
    res = gates.evaluate(rows, th, previous={"pincode_count": 100, "post_office_count": 5})
    g = next(r for r in res["results"] if r["gate"] == "pincode_count_within_pct")
    assert g["ok"] is False
    assert res["ok"] is False


def test_gate_null_coord_pct():
    th = config.Thresholds()
    rows = _norm_rows({"DELHI": ["110001", "110002"]})
    for r in rows:
        r["latitude"] = None
        r["longitude"] = None
    res = gates.evaluate(rows, th, previous=None)
    g = next(r for r in res["results"] if r["gate"] == "null_coord_pct_under_limit")
    assert g["ok"] is False  # 100% null > 20% limit


# ---- accept-baseline-change bounds ----

def test_accept_baseline_change_waives_within_10pct():
    th = config.Thresholds()
    # 5 vs 5.4% change (within 10%) but beyond the 3% pincode gate
    prev = {"pincode_count": 105, "post_office_count": 100}
    rows = _norm_rows({"DELHI": [f"1100{i:02d}" for i in range(1, 101)]})  # 100 pincodes
    res = gates.evaluate(rows, th, prev, accept_baseline_change="reason")
    g = next(r for r in res["results"] if r["gate"] == "pincode_count_within_pct")
    # The count gate specifically is downgraded to a passing warning.
    assert g["ok"] is True and g["warning"] is True
    assert res["baseline_change_waiver"] == "reason"
    # (Overall res["ok"] also depends on the all-states gate, which this synthetic
    # single-state fixture intentionally does not satisfy.)


def test_accept_baseline_change_still_fails_beyond_10pct():
    th = config.Thresholds()
    prev = {"pincode_count": 1000, "post_office_count": 100}
    rows = _norm_rows({"DELHI": [f"1{i:05d}" for i in range(1, 101)]})  # 100 pincodes (-90%)
    res = gates.evaluate(rows, th, prev, accept_baseline_change="reason")
    g = next(r for r in res["results"] if r["gate"] == "pincode_count_within_pct")
    assert g["ok"] is False   # beyond +/-10% -> not waived
    assert res["ok"] is False


# ---- prefix map precedence ----

def test_prefix_map_3digit_overrides_2digit():
    two, three = outputs._load_prefix_map()
    # 744 (Andaman) is a 3-digit override; 74 (2-digit) allows WB/A&N/Sikkim.
    assert "744" in three
    assert three["744"] == {"ANDAMAN AND NICOBAR ISLANDS"}
    assert "74" in two
    # a 744xxx pincode in ANDAMAN must NOT be flagged (3-digit wins)
    rows = _norm_rows({"ANDAMAN AND NICOBAR ISLANDS": ["744101"]})
    mism = outputs._prefix_mismatches(rows)
    assert mism == []


def test_prefix_map_flags_out_of_set():
    # 403 -> GOA only; a KERALA row at 403xxx is a mismatch
    rows = _norm_rows({"KERALA": ["403001"]})
    mism = outputs._prefix_mismatches(rows)
    assert len(mism) == 1
    assert mism[0]["state"] == "KERALA"
