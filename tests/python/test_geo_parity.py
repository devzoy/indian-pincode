"""find_nearby must equal a brute-force haversine scan on 500 random points, with
and without include_suspect."""

import math
import os
import random
import sqlite3
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "packages", "py-core"))
sys.path.insert(0, os.path.join(REPO_ROOT, "packages", "py-geo"))

import indian_pincode_geo as geo  # noqa: E402


def _haversine(a, b, c, d):
    R = 6371.0
    dl = math.radians(c - a)
    dn = math.radians(d - b)
    x = math.sin(dl / 2) ** 2 + math.cos(math.radians(a)) * math.cos(math.radians(c)) * math.sin(dn / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(x), math.sqrt(1 - x))


@pytest.fixture(scope="module")
def all_rows():
    geo.preload()
    conn = geo._conn()
    rows = conn.execute(
        "SELECT pincode, office_name, lat_e5, lon_e5, gq_code FROM post_offices"
    ).fetchall()
    # Precompute float coords once; None-coord rows dropped.
    pts = [(r["pincode"], r["office_name"], r["lat_e5"] / 1e5, r["lon_e5"] / 1e5, r["gq_code"])
           for r in rows if r["lat_e5"] is not None]
    return pts


def _brute(pts, lat, lon, radius, include_suspect):
    # Still checks every point, but skips the expensive haversine for points that
    # are provably outside the radius by a cheap latitude bound (1 deg lat ~ 111 km).
    lat_margin = radius / 111.0 + 0.001
    out = []
    for pincode, name, pla, plo, gq in pts:
        if gq == 2 and not include_suspect:
            continue
        if abs(pla - lat) > lat_margin:
            continue
        if _haversine(lat, lon, pla, plo) <= radius:
            out.append(f"{pincode}|{name}")
    return sorted(out)


@pytest.mark.parametrize("include_suspect,seed", [(False, 7), (True, 99)])
def test_find_nearby_matches_brute_force(all_rows, include_suspect, seed):
    rng = random.Random(seed)
    for _ in range(500):  # noqa: PLR2004
        lat = 6.5 + rng.random() * 31
        lon = 68 + rng.random() * 29.5
        got = sorted(
            f"{int(o['pincode'])}|{o['office_name']}"
            for o in geo.find_nearby(lat, lon, radius_km=5, limit=10_000_000,
                                     include_suspect=include_suspect)
        )
        expected = _brute(all_rows, lat, lon, 5, include_suspect)
        assert got == expected, f"mismatch at {lat},{lon}"


def test_find_nearby_rejects_invalid_coords():
    with pytest.raises(TypeError):
        geo.find_nearby(float("nan"), 77)
    with pytest.raises(TypeError):
        geo.find_nearby(28, "x")
    with pytest.raises(ValueError):
        geo.find_nearby(200, 77)
    with pytest.raises(ValueError):
        geo.find_nearby(28, 400)
