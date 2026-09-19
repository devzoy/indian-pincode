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


@pytest.fixture(scope="module")
def all_centroids():
    geo.preload()
    conn = geo._conn()
    rows = conn.execute("SELECT pincode, lat_e5, lon_e5 FROM centroids").fetchall()
    return [(r["pincode"], r["lat_e5"] / 1e5, r["lon_e5"] / 1e5) for r in rows]


def _brute_nearest(centroids, lat, lon):
    best_pin, best_dist = None, float("inf")
    for pincode, plat, plon in centroids:
        d = _haversine(lat, lon, plat, plon)
        if d < best_dist:
            best_dist, best_pin = d, pincode
    return best_pin, best_dist


def test_reverse_lookup_matches_brute_force_near_real_centroids(all_centroids):
    """Regression test for a box-search bug: an expanding-box nearest-neighbor
    search that stops at the first non-empty box can return a wrong pincode --
    a closer point can sit just outside the box, near a corner. Perturbs 2000
    points near real centroids (not uniform random ones) since that's exactly
    where the corner-miss bug bites: right at the boundary between two pincodes'
    areas of influence."""
    rng = random.Random(2024)
    sample = rng.sample(all_centroids, min(2000, len(all_centroids)))
    mismatches = []
    for pincode, lat, lon in sample:
        jlat = lat + rng.uniform(-0.02, 0.02)
        jlon = lon + rng.uniform(-0.02, 0.02)
        got = geo.reverse_lookup(jlat, jlon)
        expected_pin, expected_dist = _brute_nearest(all_centroids, jlat, jlon)
        if got is None or int(got["pincode"]) != expected_pin:
            # A genuine distance tie (different pincode, same rounded distance)
            # isn't a bug -- either is a correct nearest neighbor.
            if got is not None and abs(got["distance_km"] - expected_dist) < 0.001:
                continue
            mismatches.append((jlat, jlon, got, expected_pin, expected_dist))
    assert not mismatches, (
        f"{len(mismatches)}/{len(sample)} reverse_lookup mismatches vs. brute force: "
        f"{mismatches[:5]}"
    )


def test_reverse_lookup_max_km():
    near = geo.reverse_lookup(28.6304, 77.2177, max_km=1)
    assert near is not None
    far_ocean = geo.reverse_lookup(15.0, 68.0, max_km=1)
    assert far_ocean is None
    with pytest.raises(ValueError):
        geo.reverse_lookup(28.6, 77.2, max_km=-1)
