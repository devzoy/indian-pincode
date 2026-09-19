"""Core district/state model: cross-state pincodes must not leak districts into
the wrong state's listDistricts (the BUDAUN bug)."""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "packages", "py-core"))

import indian_pincode as core  # noqa: E402


def test_list_districts_delhi_excludes_up_district():
    districts = core.list_districts("DELHI")
    assert "BUDAUN" not in districts, "cross-state UP district leaked into DELHI"
    assert "NEW DELHI" in districts


def test_cross_state_pincode_details_110025():
    d = core.get_details("110025")
    assert d["state"] == "DELHI"                       # primary (most offices)
    assert d["states"] == ["DELHI", "UTTAR PRADESH"]   # all, sorted
    assert set(d["districts"]) == {"SOUTH", "SOUTH EAST", "BUDAUN"}


def test_get_pincodes_state_district_must_cooccur():
    # DELHI and BUDAUN never co-occur on the same office pair, so combining them
    # yields nothing, even though 110025 touches both.
    assert core.get_pincodes(state="DELHI", district="BUDAUN") == []
    assert "110025" in core.get_pincodes(state="DELHI")
    assert "110025" in core.get_pincodes(district="BUDAUN")


def test_primary_state_is_majority_ties_alphabetical():
    # 110025 has more DELHI offices than UP -> primary DELHI.
    assert core.get_details("110025")["state"] == "DELHI"


def test_multi_district_single_state():
    # a plain multi-district pincode still lists all its districts
    d = core.get_details("110001")
    assert d["state"] == "DELHI"
    assert d["states"] == ["DELHI"]
    assert "NEW DELHI" in d["districts"]
