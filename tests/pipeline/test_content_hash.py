"""content_sha256 must depend only on the cleaned data, not on input row order."""

import os
import random
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

from pipeline import outputs  # noqa: E402


def _row(pin, office, otype, state="DELHI"):
    return {
        "pincode": pin, "office_name": office, "office_type": otype,
        "delivery_status": "Delivery", "division_name": "D", "region_name": "R",
        "circle_name": "C", "district": "NEW DELHI", "state_name": state,
        "state_source": "source", "state_inferred_from_circle": None,
        "latitude": 28.6, "longitude": 77.2, "geo_quality": "original", "geo_fixed": None,
    }


def test_content_sha256_is_order_independent():
    rows = [
        _row("110001", "New Delhi GPO", "HO"),
        _row("110001", "Baroda House SO", "PO"),
        _row("110002", "Minto Road SO", "PO"),
        _row("560001", "Bangalore GPO", "HO", state="KARNATAKA"),
        _row("682555", "Kavaratti SO", "PO", state="LAKSHADWEEP"),
    ]
    base = outputs.content_sha256(rows)
    rng = random.Random(1)
    for _ in range(10):
        shuffled = rows[:]
        rng.shuffle(shuffled)
        assert outputs.content_sha256(shuffled) == base, "hash changed after shuffle"


def test_content_sha256_changes_when_data_changes():
    rows = [_row("110001", "New Delhi GPO", "HO")]
    a = outputs.content_sha256(rows)
    rows2 = [_row("110001", "New Delhi GPO", "BO")]  # different office_type
    assert outputs.content_sha256(rows2) != a


def test_total_ordering_handles_duplicate_primary_keys():
    # same pincode+name+type, differing later fields -> stable, total order
    r1 = _row("111111", "X BO", "BO"); r1["latitude"] = 20.0
    r2 = _row("111111", "X BO", "BO"); r2["latitude"] = 21.0
    base = outputs.content_sha256([r1, r2])
    assert outputs.content_sha256([r2, r1]) == base
