"""Python side of the golden-fixture parity test. Asserts core + geo output against
tests/fixtures/golden.json (neutral snake_case values; Python keys are snake_case)."""

import json
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "packages", "py-core"))
sys.path.insert(0, os.path.join(REPO_ROOT, "packages", "py-geo"))

import indian_pincode as core  # noqa: E402
import indian_pincode_geo as geo  # noqa: E402

GOLDEN = os.path.join(REPO_ROOT, "tests", "fixtures", "golden.json")


def _load():
    with open(GOLDEN, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def golden():
    return _load()


def test_golden_present_and_large(golden):
    assert golden["count"] >= 200
    assert golden["data_version"] == core.DATA_VERSION


def test_core_matches_golden(golden):
    for e in golden["entries"]:
        exp = e["core"]
        got = core.get_details(e["pincode"])
        assert got is not None, f"{e['pincode']} not found"
        assert got["pincode"] == exp["pincode"]
        assert got["state"] == exp["state"]
        assert got["states"] == exp["states"]
        assert got["state_source"] == exp["state_source"]
        assert got["districts"] == exp["districts"]
        assert core.validate(e["pincode"]) is True


def test_geo_matches_golden(golden):
    for e in golden["entries"]:
        exp = e["geo"]
        got = geo.lookup(e["pincode"])
        assert len(got) == len(exp), f"{e['pincode']} office count"
        for g_off, e_off in zip(got, exp):
            for k in ("pincode", "office_name", "office_type", "delivery_status",
                      "district", "state", "state_source", "geo_quality"):
                assert g_off[k] == e_off[k], f"{e['pincode']} {k}: {g_off[k]!r} != {e_off[k]!r}"
            # coordinates: allow tiny int32(1e-5) rounding vs source float
            for k in ("latitude", "longitude"):
                if e_off[k] is None:
                    assert g_off[k] is None
                else:
                    assert abs(g_off[k] - e_off[k]) < 1e-4
