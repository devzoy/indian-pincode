"""Invalid-input handling for core validate/getDetails and geo find_nearby."""

import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "packages", "py-core"))
sys.path.insert(0, os.path.join(REPO_ROOT, "packages", "py-geo"))

import indian_pincode as core  # noqa: E402
import indian_pincode_geo as geo  # noqa: E402


@pytest.mark.parametrize("bad", ["000000", "012345", "12345", "1234567", "abcdef", ""])
def test_validate_rejects_malformed(bad):
    assert core.validate(bad) is False
    assert core.get_details(bad) is None


def test_validate_none_and_float():
    assert core.validate(None) is False
    # a float like 110001.0 -> str "110001.0" is not 6 digits -> False
    assert core.validate(110001.0) is False
    assert core.validate("") is False


def test_is_well_formed_vs_validate():
    # well-formed but NOT in the dataset
    assert core.is_well_formed("999999") is True
    assert core.validate("999999") is False
    # 012345 has a leading zero -> not well-formed
    assert core.is_well_formed("012345") is False


def test_validate_accepts_int_and_whitespace():
    assert core.validate(110001) is True
    assert core.validate("  110001  ") is True


def test_find_nearby_invalid_coords_and_radius():
    with pytest.raises(TypeError):
        geo.find_nearby(float("nan"), 77.0)
    with pytest.raises(TypeError):
        geo.find_nearby("28", 77.0)
    with pytest.raises(ValueError):
        geo.find_nearby(-91, 77)
    with pytest.raises(ValueError):
        geo.find_nearby(28, 181)
    with pytest.raises(ValueError):
        geo.find_nearby(28.6, 77.2, radius_km=-5)


def test_lookup_unknown_returns_empty():
    assert geo.lookup("999999") == []
    assert geo.get_centroid("999999") is None
