"""Emit per-language package data artifacts from the canonical normalized dataset.

Invoked by `python -m pipeline.build --emit-packages`. Deterministic: the same
canonical input produces byte-identical package data files.

Outputs:
  core (Node)   -> packages/node-core/data/core-data.json
  core (Python) -> packages/py-core/indian_pincode/data/core-data.json
  geo (Node)    -> packages/node-geo/data/{records.json,grid.json,centroids.json}
  geo (Python)  -> packages/py-geo/indian_pincode_geo/data/geo.sqlite
"""

from __future__ import annotations

import gzip
import json
import os
import sqlite3
import time
from collections import defaultdict
from typing import Dict, List, Tuple

from . import config


def _remove_with_retry(path: str, attempts: int = 10, delay: float = 2.0) -> None:
    """Remove a file, retrying on PermissionError. Backstop for whatever is
    still holding a lock on a just-written file (observed on Windows CI even
    with real-time AV scanning disabled); ~20s worst-case budget."""
    for i in range(attempts):
        try:
            os.remove(path)
            return
        except PermissionError:
            if i == attempts - 1:
                raise
            time.sleep(delay)


PACKAGES_DIR = os.path.join(config.REPO_ROOT, "packages")

NODE_CORE_DATA = os.path.join(PACKAGES_DIR, "node-core", "data", "core-data.cjs")
PY_CORE_DATA = os.path.join(PACKAGES_DIR, "py-core", "indian_pincode", "data", "core-data.json")
NODE_GEO_DIR = os.path.join(PACKAGES_DIR, "node-geo", "data")
PY_GEO_DB = os.path.join(PACKAGES_DIR, "py-geo", "indian_pincode_geo", "data", "geo.sqlite")

COORD_SCALE = 100000  # 1e-5 degree precision -> int32
GRID_DEG = 0.1        # spatial grid cell size in degrees


def _load_rows() -> List[Dict]:
    rows = []
    with gzip.open(config.NORMALIZED_PATH, "rt", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _load_metadata() -> Dict:
    with open(config.METADATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def _load_centroids() -> Dict:
    with gzip.open(config.CENTROIDS_PATH, "rt", encoding="utf-8") as f:
        return json.load(f)


# ---- Core -----------------------------------------------------------------

def build_core_payload(rows: List[Dict], version: str) -> Dict:
    """Build the compact core payload.

    Districts are stored as (districtNameIdx, stateIdx) PAIRS, so the same
    district name in two states is two distinct entries. Each pincode references
    the set of pairs actually observed on its rows. This makes listDistricts(state)
    correct for cross-state pincodes (it uses only pairs whose state matches),
    fixing the bug where a cross-state pincode leaked another state's districts.

    Primary state per pincode = the state with the most offices; ties break
    alphabetically. getDetails returns that primary `state` plus `states` (all
    states observed for the pincode, sorted).
    """
    states = sorted({r["state_name"] for r in rows if r["state_name"]})
    districts = sorted({r["district"] for r in rows if r["district"]})
    state_id = {s: i for i, s in enumerate(states)}
    district_id = {d: i for i, d in enumerate(districts)}

    # EVERY pincode present must be included so validate() is true for all.
    all_pincodes: set = set()
    pin_state_counts: Dict[str, defaultdict] = defaultdict(lambda: defaultdict(int))
    pin_pairs: Dict[str, set] = defaultdict(set)          # {pincode: {(state_id, district_id)}}
    pin_state_source: Dict[str, Dict[str, str]] = defaultdict(dict)
    for r in rows:
        p = r["pincode"]
        all_pincodes.add(p)
        sid = state_id[r["state_name"]] if r["state_name"] else -1
        if r["state_name"]:
            pin_state_counts[p][r["state_name"]] += 1
            existing = pin_state_source[p].get(r["state_name"])
            if existing is None or r["state_source"] == "source":
                pin_state_source[p][r["state_name"]] = r["state_source"]
        if r["district"]:
            pin_pairs[p].add((sid, district_id[r["district"]]))

    # Build the global (state_id, district_id) pair table, deterministically ordered.
    all_pairs = sorted({pair for pairs in pin_pairs.values() for pair in pairs})
    pair_id = {pair: i for i, pair in enumerate(all_pairs)}
    # districtPairs[i] = [districtNameIdx, stateIdx] (stateIdx may be -1)
    district_pairs = [[d, s] for (s, d) in all_pairs]

    source_codes = ["source", "inferred_pincode", "inferred_circle", "null"]
    source_id = {s: i for i, s in enumerate(source_codes)}

    pincodes_sorted = sorted(int(p) for p in all_pincodes)
    deltas = []
    prev = 0
    for p in pincodes_sorted:
        deltas.append(p - prev)
        prev = p

    source_default = source_id["source"]  # 0
    state_idx = []
    # statesAll is sparse: for the ~99.7% single-state pincodes, `states` is just
    # [stateIdx]; only cross-state pincodes need an explicit list.
    states_all_sparse = {}    # {pincodeIndex: [stateId,...]} when >1 state
    state_source_sparse = {}  # {pincodeIndex: code} for codes != "source"
    pair_groups = []
    for idx, p in enumerate(pincodes_sorted):
        ps = str(p).zfill(6)
        counts = pin_state_counts.get(ps)
        if counts:
            best = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
            state_idx.append(state_id[best])
            code = source_id.get(pin_state_source[ps].get(best, "source"), 0)
            all_ids = sorted(state_id[s] for s in counts)
            if len(all_ids) > 1:
                states_all_sparse[str(idx)] = all_ids
        else:
            state_idx.append(-1)
            code = source_id["null"]
        if code != source_default:
            state_source_sparse[str(idx)] = code
        pids = sorted(pair_id[pair] for pair in pin_pairs.get(ps, set()))
        if len(pids) == 1:
            pair_groups.append(pids[0])
        else:
            pair_groups.append(pids)  # 0 -> [], or multi -> [..]

    return {
        "version": version,
        "states": states,
        "districts": districts,
        "districtPairs": district_pairs,
        "stateSources": source_codes,
        "stateSourceDefault": source_default,
        "pincodes": deltas,
        "stateIdx": state_idx,
        "statesAllSparse": states_all_sparse,
        "stateSourceSparse": state_source_sparse,
        "pairGroups": pair_groups,
    }


def _write_json(path: str, obj: Dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        # Compact separators; sort_keys for determinism.
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def emit_core(rows: List[Dict], version: str) -> Dict:
    payload = build_core_payload(rows, version)
    # Python core reads the JSON via importlib.resources.
    _write_json(PY_CORE_DATA, payload)
    # Node core ships ONE data module: data/core-data.cjs (module.exports = {...}).
    # The CJS entry require()s it; the ESM entry does `import data from
    # '../data/core-data.cjs'` (Node ESM imports CJS natively as the default
    # export). esbuild keeps it external for the shipped dist (single copy) and
    # inlines it only when bundling for the browser.
    compact = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    node_dir = os.path.dirname(NODE_CORE_DATA)
    os.makedirs(node_dir, exist_ok=True)
    with open(os.path.join(node_dir, "core-data.cjs"), "w", encoding="utf-8") as f:
        f.write("'use strict';\nmodule.exports=" + compact + ";\n")
    return {
        "pincodes": len(payload["pincodes"]),
        "states": len(payload["states"]),
        "districts": len(payload["districts"]),
        "state_source_sparse": len(payload["stateSourceSparse"]),
    }


# ---- Geo (Node) -----------------------------------------------------------

def _scale(v):
    return None if v is None else int(round(v * COORD_SCALE))


_DELIVERY_CODE = {"Delivery": 1, "Non Delivery": 0}
_GEO_QUALITY_CODES = ["original", "swapped", "suspect", "removed", "missing"]
_STATE_SOURCE_CODES = ["source", "inferred_pincode", "inferred_circle", "null"]


def emit_geo_node(rows: List[Dict], centroids: Dict, version: str) -> Dict:
    """Emit Node geo using string tables + integer codes to keep size small.

    Record layout (array per office):
      [pincode, officeName, typeCode, deliveryCode, districtId, stateId,
       lat_int32|null, lon_int32|null, geoQualityCode]
    where typeCode: 0=HO 1=PO 2=BO; deliveryCode: 1=Delivery 0=Non Delivery;
    districtId/stateId index into districts[]/states[] (-1 for null);
    geoQualityCode indexes GEO_QUALITY. Coords are int32 at 1e-5 deg.
    """
    type_order = config.OFFICE_TYPE_ORDER
    ordered = sorted(
        rows,
        key=lambda r: (r["pincode"], type_order.get(r["office_type"], 9), r["office_name"]),
    )

    states = sorted({r["state_name"] for r in rows if r["state_name"]})
    districts = sorted({r["district"] for r in rows if r["district"]})
    state_id = {s: i for i, s in enumerate(states)}
    district_id = {d: i for i, d in enumerate(districts)}
    gq_id = {g: i for i, g in enumerate(_GEO_QUALITY_CODES)}
    ss_id = {s: i for i, s in enumerate(_STATE_SOURCE_CODES)}

    records = []
    grid = defaultdict(list)
    for idx, r in enumerate(ordered):
        lat = _scale(r["latitude"])
        lon = _scale(r["longitude"])
        records.append([
            r["pincode"],
            r["office_name"],
            type_order.get(r["office_type"], 9),
            _DELIVERY_CODE.get(r["delivery_status"], 1),
            district_id.get(r["district"], -1) if r["district"] else -1,
            state_id.get(r["state_name"], -1) if r["state_name"] else -1,
            lat, lon,
            gq_id.get(r["geo_quality"], 0),
            ss_id.get(r["state_source"], 3),
        ])
        if lat is not None and lon is not None:
            grid[_cell_key(r["latitude"], r["longitude"])].append(idx)

    cent = {}
    for pin, c in centroids.items():
        cent[pin] = [_scale(c["latitude"]), _scale(c["longitude"])]

    os.makedirs(NODE_GEO_DIR, exist_ok=True)
    # Gzip the geo shards: they are decompressed once, lazily, at runtime. This
    # keeps the installed package well within the size budget (~3 MB vs ~12 MB).
    _write_json_gz(os.path.join(NODE_GEO_DIR, "records.json.gz"), {
        "version": version,
        "scale": COORD_SCALE,
        "states": states,
        "districts": districts,
        "geoQuality": _GEO_QUALITY_CODES,
        "stateSources": _STATE_SOURCE_CODES,
        "records": records,
    })
    _write_json_gz(os.path.join(NODE_GEO_DIR, "grid.json.gz"),
                   {"gridDeg": GRID_DEG, "cells": {k: v for k, v in sorted(grid.items())}})
    _write_json_gz(os.path.join(NODE_GEO_DIR, "centroids.json.gz"),
                   {"scale": COORD_SCALE, "centroids": cent})
    return {"records": len(records), "grid_cells": len(grid), "centroids": len(cent)}


def _write_json_gz(path: str, obj: Dict) -> None:
    import gzip
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    with gzip.GzipFile(path, "wb", mtime=0) as gz:
        gz.write(payload.encode("utf-8"))


def _cell_key(lat: float, lon: float) -> str:
    import math
    return f"{math.floor(lat / GRID_DEG)},{math.floor(lon / GRID_DEG)}"


# Packed integer grid-cell key for the Python SQLite index. lat/lon cells are
# small (India spans lat cells ~60-380, lon cells ~680-980 at 0.1deg), so we pack
# as latCell * 100000 + lonCell with a +5000/+50000 offset to stay non-negative.
_CELL_LAT_OFFSET = 5000
_CELL_LON_OFFSET = 50000
_CELL_LON_MOD = 100000


def _cell_int(lat, lon):
    import math
    if lat is None or lon is None:
        return None
    la = math.floor(lat / GRID_DEG) + _CELL_LAT_OFFSET
    lo = math.floor(lon / GRID_DEG) + _CELL_LON_OFFSET
    return la * _CELL_LON_MOD + lo


# ---- Geo (Python) ---------------------------------------------------------

def emit_geo_python(rows: List[Dict], centroids: Dict, version: str) -> Dict:
    """Emit a compact SQLite DB. State/district are normalized into lookup tables
    referenced by integer id; office type/delivery/geo_quality are integer codes.
    This keeps the file small while preserving bbox+haversine query support."""
    os.makedirs(os.path.dirname(PY_GEO_DB), exist_ok=True)
    if os.path.exists(PY_GEO_DB):
        _remove_with_retry(PY_GEO_DB)
    conn = sqlite3.connect(PY_GEO_DB)
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA page_size=4096")
        cur.execute("CREATE TABLE states (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
        cur.execute("CREATE TABLE districts (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
        # pincode + coords as INTEGER (int32, 1e-5 deg) keep the table compact.
        # Rows are inserted ordered by pincode; a small pincode index supports
        # lookup and a lat/lon index supports the find_nearby bounding box. Both
        # indexes reference the compact integer rowid.
        cur.execute("""
            CREATE TABLE post_offices (
                pincode INTEGER NOT NULL,
                office_name TEXT NOT NULL,
                type_code INTEGER NOT NULL,      -- 0=HO 1=PO 2=BO
                delivery_code INTEGER NOT NULL,  -- 1=Delivery 0=Non Delivery
                district_id INTEGER,             -- FK -> districts.id, NULL if none
                state_id INTEGER,                -- FK -> states.id, NULL if none
                lat_e5 INTEGER,                  -- round(lat * 1e5), NULL if none
                lon_e5 INTEGER,                  -- round(lon * 1e5), NULL if none
                gq_code INTEGER NOT NULL,        -- index into GEO_QUALITY
                ss_code INTEGER NOT NULL,        -- index into STATE_SOURCE
                cell INTEGER                     -- 0.1deg grid cell key, NULL if no coords
            )
        """)
        cur.execute("CREATE TABLE centroids (pincode INTEGER PRIMARY KEY, lat_e5 INTEGER, lon_e5 INTEGER)")
        cur.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")

        states = sorted({r["state_name"] for r in rows if r["state_name"]})
        districts = sorted({r["district"] for r in rows if r["district"]})
        state_id = {s: i for i, s in enumerate(states)}
        district_id = {d: i for i, d in enumerate(districts)}
        cur.executemany("INSERT INTO states VALUES (?,?)", list(enumerate(states)))
        cur.executemany("INSERT INTO districts VALUES (?,?)", list(enumerate(districts)))

        type_order = config.OFFICE_TYPE_ORDER
        gq_id = {g: i for i, g in enumerate(_GEO_QUALITY_CODES)}
        ss_id = {s: i for i, s in enumerate(_STATE_SOURCE_CODES)}
        ordered = sorted(
            rows,
            key=lambda r: (r["pincode"], type_order.get(r["office_type"], 9), r["office_name"]),
        )
        cur.executemany(
            "INSERT INTO post_offices VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            [(int(r["pincode"]), r["office_name"],
              type_order.get(r["office_type"], 9),
              _DELIVERY_CODE.get(r["delivery_status"], 1),
              district_id.get(r["district"]) if r["district"] else None,
              state_id.get(r["state_name"]) if r["state_name"] else None,
              _scale(r["latitude"]), _scale(r["longitude"]),
              gq_id.get(r["geo_quality"], 0),
              ss_id.get(r["state_source"], 3),
              _cell_int(r["latitude"], r["longitude"]))
             for r in ordered],
        )
        cur.executemany(
            "INSERT INTO centroids VALUES (?,?,?)",
            [(int(pin), _scale(c["latitude"]), _scale(c["longitude"]))
             for pin, c in sorted(centroids.items())],
        )
        cur.execute("INSERT INTO meta VALUES ('version', ?)", (version,))
        cur.execute("INSERT INTO meta VALUES ('geo_quality', ?)", (",".join(_GEO_QUALITY_CODES),))
        cur.execute("INSERT INTO meta VALUES ('coord_scale', ?)", (str(COORD_SCALE),))
        cur.execute("INSERT INTO meta VALUES ('grid_deg', ?)", (str(GRID_DEG),))
        # A single-integer grid-cell index is much smaller than a (lat,lon) index
        # and supports find_nearby by scanning only the cells overlapping the radius.
        # We deliberately DO NOT add a pincode index: it would add ~1.9 MB and push
        # the file over the 10 MB budget. Rows are stored in pincode order, so we
        # build a compact in-memory pincode -> rowid-range map at load time instead
        # (see the geo package), keeping lookup fast without the on-disk index.
        cur.execute("CREATE INDEX idx_po_cell ON post_offices(cell)")
        cur.execute("INSERT INTO meta VALUES ('rows_sorted_by_pincode', '1')")
        conn.commit()
        cur.execute("VACUUM")
        conn.commit()
        n = cur.execute("SELECT COUNT(*) FROM post_offices").fetchone()[0]
    finally:
        conn.close()
    return {"post_offices": n, "centroids": len(centroids)}


# ---- Orchestrator ---------------------------------------------------------

def emit_all() -> Dict:
    rows = _load_rows()
    meta = _load_metadata()
    centroids = _load_centroids()
    version = meta["data_version"]
    core = emit_core(rows, version)
    geo_node = emit_geo_node(rows, centroids, version)
    geo_py = emit_geo_python(rows, centroids, version)
    print(f"[emit] core: {core}")
    print(f"[emit] geo(node): {geo_node}")
    print(f"[emit] geo(python): {geo_py}")
    return {"core": core, "geo_node": geo_node, "geo_python": geo_py, "version": version}
