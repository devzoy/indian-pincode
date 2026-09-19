"""indian-pincode-geo: post offices, coordinates, nearby search, reverse lookup.

Companion to `indian-pincode` (core). Data is a compact SQLite database loaded
lazily via importlib.resources. find_nearby uses a bounding-box prefilter plus a
haversine filter (no dependency on the SQLite R*Tree module).

Importing this package also patches the core module so that
`indian_pincode.lookup(...)` etc. work (instead of raising ImportError).
"""

from __future__ import annotations

import math
import sqlite3
import threading
from importlib import resources
from typing import Dict, List, Optional, TypedDict, Union

__all__ = [
    "lookup", "find_nearby", "reverse_lookup", "get_centroid", "preload",
    "PostOffice", "NearbyPostOffice",
]

_LOCK = threading.RLock()
_CONN = None
_TYPE_NAME = ["HO", "PO", "BO"]
_DELIVERY_NAME = ["Non Delivery", "Delivery"]
_GEO_QUALITY = ["original", "swapped", "suspect", "removed", "missing"]
_STATE_SOURCE = ["source", "inferred_pincode", "inferred_circle", "null"]

_SCALE = 100000  # 1e-5 degree precision (matches emitter COORD_SCALE)

# Base SELECT that decodes FK ids and codes back to strings via joins.
_SELECT = """
    SELECT po.pincode AS pincode,
           po.office_name AS office_name,
           po.type_code AS type_code,
           po.delivery_code AS delivery_code,
           d.name AS district,
           s.name AS state,
           po.lat_e5 AS lat_e5,
           po.lon_e5 AS lon_e5,
           po.gq_code AS gq_code,
           po.ss_code AS ss_code
    FROM post_offices po
    LEFT JOIN states s ON s.id = po.state_id
    LEFT JOIN districts d ON d.id = po.district_id
"""


def _coord(e5):
    return None if e5 is None else e5 / _SCALE


# Grid-cell packing (must match pipeline/emit.py).
_GRID_DEG = 0.1
_CELL_LAT_OFFSET = 5000
_CELL_LON_OFFSET = 50000
_CELL_LON_MOD = 100000


def _cell_int(lat_cell: int, lon_cell: int) -> int:
    return (lat_cell + _CELL_LAT_OFFSET) * _CELL_LON_MOD + (lon_cell + _CELL_LON_OFFSET)


def _cells_for_radius(lat: float, lon: float, radius_km: float) -> List[int]:
    lat_cell = math.floor(lat / _GRID_DEG)
    lon_cell = math.floor(lon / _GRID_DEG)
    lat_span = int(math.ceil(radius_km / 111.0 / _GRID_DEG)) + 1
    lon_span = int(math.ceil(
        radius_km / (111.0 * max(0.01, math.cos(math.radians(lat)))) / _GRID_DEG)) + 1
    cells = []
    for dla in range(-lat_span, lat_span + 1):
        for dlo in range(-lon_span, lon_span + 1):
            cells.append(_cell_int(lat_cell + dla, lon_cell + dlo))
    return cells


class PostOffice(TypedDict):
    pincode: str
    office_name: str
    office_type: str
    delivery_status: str
    district: Optional[str]
    state: Optional[str]
    state_source: str
    latitude: Optional[float]
    longitude: Optional[float]
    geo_quality: str


class NearbyPostOffice(PostOffice):
    distance_km: float


_DB_CTX = None  # keeps the as_file() context alive for the process lifetime


def _db_path() -> str:
    """Resolve the on-disk path to the bundled SQLite via importlib.resources.

    Uses files()+as_file() so it works whether the package is imported from a
    directory or a zipimport; the extracted temp path (if any) is kept alive for
    the process via _DB_CTX."""
    global _DB_CTX
    res = resources.files(__package__).joinpath("data/geo.sqlite")
    _DB_CTX = resources.as_file(res)
    return str(_DB_CTX.__enter__())


def _conn():
    global _CONN
    if _CONN is None:
        with _LOCK:
            if _CONN is None:
                path = _db_path()
                # Open read-only + immutable: the DB never changes at runtime, so
                # this avoids WAL/journal files and is safe for concurrent reads.
                uri = f"file:{_pathname2url(path)}?mode=ro&immutable=1"
                c = sqlite3.connect(uri, uri=True, check_same_thread=False)
                c.row_factory = sqlite3.Row
                _CONN = c
    return _CONN


def _pathname2url(path: str) -> str:
    # Build the path portion of a file: URI (handles spaces/special chars, and
    # Windows drive letters).
    from urllib.request import pathname2url
    return pathname2url(path)


_PIN_ROWIDS = None  # sorted list of pincodes, parallel to rowids (rowid == index+1)


def _pin_index():
    """Lazily build a pincode->rowid-range index in memory. The DB stores rows in
    pincode order (rowid order), so we load the pincode column once and binary
    search it. This avoids shipping a ~1.9 MB on-disk pincode index (size budget)."""
    global _PIN_ROWIDS
    if _PIN_ROWIDS is None:
        with _LOCK:
            if _PIN_ROWIDS is None:
                rows = _conn().execute(
                    "SELECT pincode FROM post_offices ORDER BY rowid"
                ).fetchall()
                _PIN_ROWIDS = [r[0] for r in rows]
    return _PIN_ROWIDS


def preload() -> None:
    """Eagerly open the geo database and build the in-memory pincode index."""
    _conn()
    _pin_index()


def _row_to_office(row: sqlite3.Row) -> PostOffice:
    tc = row["type_code"]
    return {
        "pincode": f"{row['pincode']:06d}",
        "office_name": row["office_name"],
        "office_type": _TYPE_NAME[tc] if 0 <= tc < len(_TYPE_NAME) else str(tc),
        "delivery_status": _DELIVERY_NAME[row["delivery_code"]],
        "district": row["district"],
        "state": row["state"],
        "state_source": _STATE_SOURCE[row["ss_code"]],
        "latitude": _coord(row["lat_e5"]),
        "longitude": _coord(row["lon_e5"]),
        "geo_quality": _GEO_QUALITY[row["gq_code"]],
    }


def _pin_int(pin: Union[str, int]) -> Optional[int]:
    s = str(pin).strip()
    return int(s) if s.isdigit() else None


def lookup(pin: Union[str, int]) -> List[PostOffice]:
    """All post offices for a pincode, sorted HO, PO, BO, then office name."""
    pi = _pin_int(pin)
    if pi is None:
        return []
    from bisect import bisect_left, bisect_right
    pins = _pin_index()
    lo = bisect_left(pins, pi)
    hi = bisect_right(pins, pi)
    if lo == hi:
        return []
    # rowids are 1-based and contiguous for a pincode (rows sorted by pincode).
    with _LOCK:
        rows = _conn().execute(
            _SELECT + " WHERE po.rowid BETWEEN ? AND ?", (lo + 1, hi)
        ).fetchall()
    offices = [_row_to_office(r) for r in rows]
    offices.sort(key=lambda o: (_TYPE_NAME.index(o["office_type"])
                                if o["office_type"] in _TYPE_NAME else 9,
                                o["office_name"]))
    return offices


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _validate_coords(lat, lon) -> None:
    if isinstance(lat, bool) or isinstance(lon, bool):
        raise TypeError("latitude and longitude must be numbers")
    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        raise TypeError("latitude and longitude must be numbers")
    if math.isnan(lat) or math.isnan(lon) or math.isinf(lat) or math.isinf(lon):
        raise TypeError("latitude and longitude must be finite numbers")
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        raise ValueError("latitude/longitude out of range")


def find_nearby(
    lat: float,
    lon: float,
    radius_km: float = 5.0,
    limit: int = 20,
    include_suspect: bool = False,
) -> List[NearbyPostOffice]:
    """Post offices within radius_km of (lat, lon), sorted by distance.

    Uses a bounding-box prefilter then a haversine filter. Suspect-quality points
    are excluded unless include_suspect=True."""
    _validate_coords(lat, lon)
    if not isinstance(radius_km, (int, float)) or isinstance(radius_km, bool) \
            or math.isnan(radius_km) or radius_km < 0:
        raise ValueError("radius_km must be a non-negative number")
    # Query only the 0.1deg grid cells overlapping the search circle, then filter
    # by haversine. This scans a bounded set of cells, never the full table.
    cells = _cells_for_radius(lat, lon, radius_km)
    placeholders = ",".join("?" for _ in cells)
    sql = _SELECT + f" WHERE po.cell IN ({placeholders})"
    params = list(cells)
    if not include_suspect:
        sql += " AND po.gq_code != 2"  # 2 == 'suspect'
    with _LOCK:
        rows = _conn().execute(sql, params).fetchall()

    out: List[NearbyPostOffice] = []
    for r in rows:
        rlat = _coord(r["lat_e5"])
        rlon = _coord(r["lon_e5"])
        if rlat is None or rlon is None:
            continue
        dist = _haversine_km(lat, lon, rlat, rlon)
        if dist <= radius_km:
            office = dict(_row_to_office(r))
            office["distance_km"] = round(dist, 3)
            out.append(office)  # type: ignore[arg-type]
    out.sort(key=lambda o: o["distance_km"])
    if limit is not None and limit >= 0:
        out = out[:limit]
    return out


def _centroid_box(lat: float, lon: float, radius_km: float):
    lat_change = radius_km / 111.0
    lon_change = radius_km / (111.0 * max(0.01, math.cos(math.radians(lat))))
    with _LOCK:
        return _conn().execute(
            "SELECT pincode, lat_e5, lon_e5 FROM centroids "
            "WHERE lat_e5 BETWEEN ? AND ? AND lon_e5 BETWEEN ? AND ?",
            (int((lat - lat_change) * _SCALE), int((lat + lat_change) * _SCALE),
             int((lon - lon_change) * _SCALE), int((lon + lon_change) * _SCALE)),
        ).fetchall()


def _closest_in_rows(lat: float, lon: float, rows) -> Optional[Dict]:
    best = None
    for r in rows:
        dist = _haversine_km(lat, lon, _coord(r["lat_e5"]), _coord(r["lon_e5"]))
        if best is None or dist < best["distance_km"]:
            best = {"pincode": f"{r['pincode']:06d}", "distance_km": round(dist, 3)}
    return best


def reverse_lookup(lat: float, lon: float, max_km: Optional[float] = None) -> Optional[Dict]:
    """Nearest pincode centroid: {'pincode', 'distance_km'} | None.

    If max_km is given, returns None when the nearest centroid is farther than
    that (e.g. to avoid treating open-ocean coordinates as a real match)."""
    _validate_coords(lat, lon)
    if max_km is not None and (
        isinstance(max_km, bool) or not isinstance(max_km, (int, float))
        or math.isnan(max_km) or max_km < 0
    ):
        raise ValueError("max_km must be a non-negative number")

    # Expand a square box until it contains at least one centroid.
    best = None
    for radius in (0.5, 1, 2, 5, 10, 25, 50, 100, 250, 500):
        rows = _centroid_box(lat, lon, radius)
        if not rows:
            continue
        best = _closest_in_rows(lat, lon, rows)
        break
    if best is None:
        return None

    # The box that found `best` doesn't necessarily contain every point within
    # `best`'s true distance -- a closer point can sit just outside the box,
    # near a corner (the box's corners are ~1.41x farther than its edges). A
    # square of half-width `best["distance_km"]` is guaranteed to fully
    # contain the circle of that radius, so re-querying at that size and
    # taking the minimum over the result is guaranteed to find the true
    # nearest centroid.
    rows = _centroid_box(lat, lon, best["distance_km"])
    closer = _closest_in_rows(lat, lon, rows)
    if closer is not None and closer["distance_km"] < best["distance_km"]:
        best = closer

    if max_km is not None and best["distance_km"] > max_km:
        return None
    return best


def get_centroid(pin: Union[str, int]) -> Optional[Dict]:
    """Centroid of a pincode: {'latitude', 'longitude'} | None."""
    pi = _pin_int(pin)
    if pi is None:
        return None
    with _LOCK:
        row = _conn().execute(
            "SELECT lat_e5, lon_e5 FROM centroids WHERE pincode = ?", (pi,)
        ).fetchone()
    if row is None:
        return None
    return {"latitude": _coord(row["lat_e5"]), "longitude": _coord(row["lon_e5"])}


# ---- patch the core module so indian_pincode.lookup(...) works --------------

def data_version() -> Optional[str]:
    """The geo data snapshot version (from the SQLite meta table)."""
    with _LOCK:
        row = _conn().execute("SELECT value FROM meta WHERE key='version'").fetchone()
    return row[0] if row else None


def _patch_core() -> None:
    try:
        import indian_pincode as _core
    except ImportError:
        return
    _core.lookup = lookup
    _core.find_nearby = find_nearby
    _core.reverse_lookup = reverse_lookup
    _core.get_centroid = get_centroid
    # Warn (do not fail) if the installed core and geo data snapshots disagree.
    try:
        core_v = _core.DATA_VERSION
        geo_v = data_version()
        if core_v and geo_v and core_v != geo_v:
            import warnings
            warnings.warn(
                f"indian-pincode core DATA_VERSION ({core_v}) != indian-pincode-geo "
                f"data version ({geo_v}). Install matching versions to avoid "
                "inconsistent results.",
                RuntimeWarning, stacklevel=2,
            )
    except Exception:  # noqa: BLE001 - never let the version check break import
        pass


_patch_core()
