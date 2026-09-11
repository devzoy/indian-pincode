"""Coordinate cleaning step.

Rules applied in order (counts recorded for the report):
  1. Parse: "NA"/empty/non-numeric -> null.
  2. Partial: exactly one of lat/lon null -> both null, geo_quality="missing".
  3. Bounding box: valid if inside [lat_min,lat_max] x [lon_min,lon_max].
  4. Swap: if outside box but (lon,lat) is inside, swap -> geo_quality="swapped",
     geo_fixed="swapped".
  5. Still outside after swap (or garbage) -> null, geo_quality="removed",
     geo_fixed="outlier_removed" is NOT used here (that's for suspects); removed
     coordinates are set to null.
  6. Outliers -> geo_quality="suspect" (coordinates kept, not nulled):
       primary: distance from same-pincode sibling median (needs >= sibling_min_count
                valid siblings); flag if > sibling_flag_km.
       fallback (< sibling_min_count siblings): distance from district median
                (needs >= district_min_count district points); flag if
                > max(district_hard_km, district_p95_multiplier * district p95).
  7. Per-pincode centroid computed from non-suspect, non-null coordinates.

geo_quality: original | swapped | removed | missing | suspect
"""

from __future__ import annotations

import math
import random
import statistics
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from . import config


def _parse(value: str) -> Optional[float]:
    if value is None:
        return None
    v = value.strip()
    if v == "" or v.upper() == "NA":
        return None
    try:
        return float(v)
    except ValueError:
        return None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def clean(rows: List[Dict], th: config.Thresholds, seed: int = 42) -> Tuple[List[Dict], Dict]:
    stats = {
        "parsed_null": 0,          # both NA/empty/nonnumeric to begin with
        "partial_missing": 0,      # exactly one of lat/lon null
        "in_box_original": 0,
        "swapped": 0,
        "removed_out_of_box": 0,
        "suspect_sibling": 0,
        "suspect_district": 0,
        "geo_quality": defaultdict(int),
    }
    flagged_samples = []

    def in_box(lat, lon):
        return (th.lat_min <= lat <= th.lat_max) and (th.lon_min <= lon <= th.lon_max)

    # Pass 1: parse, partial, bbox, swap, remove.
    for row in rows:
        lat = _parse(row.get("lat_raw"))
        lon = _parse(row.get("lon_raw"))

        if lat is None and lon is None:
            row["latitude"], row["longitude"] = None, None
            row["geo_quality"] = "missing"
            row["geo_fixed"] = None
            stats["parsed_null"] += 1
            continue
        if (lat is None) != (lon is None):
            # partial -> both null
            row["latitude"], row["longitude"] = None, None
            row["geo_quality"] = "missing"
            row["geo_fixed"] = None
            stats["partial_missing"] += 1
            continue

        if in_box(lat, lon):
            row["latitude"], row["longitude"] = lat, lon
            row["geo_quality"] = "original"
            row["geo_fixed"] = None
            stats["in_box_original"] += 1
        elif in_box(lon, lat):
            row["latitude"], row["longitude"] = lon, lat
            row["geo_quality"] = "swapped"
            row["geo_fixed"] = "swapped"
            stats["swapped"] += 1
        else:
            # out of box and swap doesn't help, or garbage (e.g. lon=7.5e9)
            row["latitude"], row["longitude"] = None, None
            row["geo_quality"] = "removed"
            row["geo_fixed"] = None
            stats["removed_out_of_box"] += 1

    # Pass 2: outlier detection (only on rows that currently have coords:
    # original or swapped).
    _flag_outliers(rows, th, stats, flagged_samples, seed)

    # Pass 3: per-pincode centroid from non-suspect, non-null coords.
    centroids = _centroids(rows)

    for row in rows:
        stats["geo_quality"][row["geo_quality"]] += 1
    stats["geo_quality"] = dict(stats["geo_quality"])
    stats["flagged_samples"] = flagged_samples
    return rows, {"stats": stats, "centroids": centroids}


def _flag_outliers(rows, th, stats, flagged_samples, seed):
    # Group valid (coord-bearing) rows by pincode and by district.
    by_pin = defaultdict(list)
    by_district = defaultdict(list)
    for row in rows:
        if row["latitude"] is None:
            continue
        by_pin[row["pincode"]].append(row)
        dkey = (row["state_name"], row["district"])
        by_district[dkey].append(row)

    # Precompute district medians and p95 of intra-district distance to median.
    district_median = {}
    district_threshold = {}
    for dkey, pts in by_district.items():
        if len(pts) < th.district_min_count:
            continue
        mlat = statistics.median(p["latitude"] for p in pts)
        mlon = statistics.median(p["longitude"] for p in pts)
        district_median[dkey] = (mlat, mlon)
        dists = sorted(haversine_km(mlat, mlon, p["latitude"], p["longitude"]) for p in pts)
        p95 = dists[min(len(dists) - 1, int(len(dists) * 0.95))]
        district_threshold[dkey] = max(th.district_hard_km, th.district_p95_multiplier * p95)

    all_flagged = []
    sibling_distances = []  # full distribution for the report
    for row in rows:
        if row["latitude"] is None:
            continue
        pin = row["pincode"]
        siblings = [s for s in by_pin[pin] if s is not row]
        valid_sibs = [(s["latitude"], s["longitude"]) for s in siblings]

        flagged = False
        reason = None
        dist = None
        if len(valid_sibs) >= th.sibling_min_count:
            mlat = statistics.median(la for la, lo in valid_sibs)
            mlon = statistics.median(lo for la, lo in valid_sibs)
            dist = haversine_km(mlat, mlon, row["latitude"], row["longitude"])
            sibling_distances.append(dist)
            if dist > th.sibling_flag_km:
                flagged = True
                reason = "sibling"
                stats["suspect_sibling"] += 1
        else:
            dkey = (row["state_name"], row["district"])
            if dkey in district_median:
                mlat, mlon = district_median[dkey]
                dist = haversine_km(mlat, mlon, row["latitude"], row["longitude"])
                if dist > district_threshold[dkey]:
                    flagged = True
                    reason = "district"
                    stats["suspect_district"] += 1

        if flagged:
            row["geo_quality"] = "suspect"
            all_flagged.append({
                "pincode": pin,
                "office_name": row["office_name"],
                "state_name": row["state_name"],
                "district": row["district"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "reason": reason,
                "distance_km": round(dist, 2) if dist is not None else None,
            })

    # Sample up to 20 flagged rows deterministically for the report.
    rng = random.Random(seed)
    if all_flagged:
        sample = rng.sample(all_flagged, min(20, len(all_flagged)))
        flagged_samples.extend(sample)

    # Sibling-distance distribution for the report (percentiles + threshold counts).
    sibling_distances.sort()
    n = len(sibling_distances)
    if n:
        def _p(p):
            return round(sibling_distances[min(n - 1, int(n * p))], 2)
        stats["sibling_distance_distribution"] = {
            "n": n,
            "p50": _p(0.50), "p75": _p(0.75), "p90": _p(0.90),
            "p95": _p(0.95), "p99": _p(0.99),
            "max": round(sibling_distances[-1], 2),
            "over_km": {
                str(t): sum(1 for d in sibling_distances if d > t)
                for t in (25, 50, 75, 100, 150, 200)
            },
            "threshold_km": th.sibling_flag_km,
        }


def _centroids(rows) -> Dict[str, Dict[str, float]]:
    by_pin = defaultdict(list)
    for row in rows:
        if row["latitude"] is None or row["geo_quality"] == "suspect":
            continue
        by_pin[row["pincode"]].append((row["latitude"], row["longitude"]))
    centroids = {}
    for pin, pts in by_pin.items():
        n = len(pts)
        centroids[pin] = {
            "latitude": round(sum(p[0] for p in pts) / n, 6),
            "longitude": round(sum(p[1] for p in pts) / n, 6),
            "n": n,
        }
    return centroids
