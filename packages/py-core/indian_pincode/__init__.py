"""indian-pincode core: validation + pincode -> state/district(s).

Offline, synchronous, memoized. Loads a compact data module via
importlib.resources. No coordinates here; install indian-pincode[geo] for
post offices and geospatial search.
"""

from __future__ import annotations

import json
import re
import threading
from bisect import bisect_left
from importlib import resources
from typing import Dict, List, Optional, TypedDict, Union

__all__ = [
    "validate", "is_well_formed", "get_details", "get_state", "get_districts",
    "list_states", "list_districts", "get_pincodes", "preload", "DATA_VERSION",
    "lookup", "find_nearby", "reverse_lookup", "get_centroid",
    "search_districts",  # deprecated v1 alias
    "PincodeDetails",
]

_WELL_FORMED = re.compile(r"^[1-9][0-9]{5}$")

_LOCK = threading.RLock()
_DATA = None  # decoded, memoized


class PincodeDetails(TypedDict):
    pincode: str
    state: Optional[str]
    state_source: str
    districts: List[str]


def _load():
    global _DATA
    if _DATA is not None:
        return _DATA
    with _LOCK:
        if _DATA is not None:
            return _DATA
        with resources.files(__package__).joinpath("data/core-data.json").open(
            "r", encoding="utf-8"
        ) as f:
            payload = json.load(f)
        # Reconstruct sorted pincodes from deltas.
        pins: List[int] = []
        acc = 0
        for delta in payload["pincodes"]:
            acc += delta
            pins.append(acc)
        _DATA = {
            "version": payload["version"],
            "states": payload["states"],
            "districts": payload["districts"],
            "state_sources": payload["stateSources"],
            "pins": pins,
            "state_idx": payload["stateIdx"],
            "state_source_idx": payload["stateSourceIdx"],
            "district_groups": payload["districtGroups"],
        }
        return _DATA


def preload() -> None:
    """Eagerly load and decode the dataset (optional; the library is lazy)."""
    _load()


def _normalize(pin: Union[str, int]) -> str:
    return str(pin).strip()


def is_well_formed(pin: Union[str, int]) -> bool:
    """Format-only check: 6 digits, no leading zero. Does not check existence."""
    return bool(_WELL_FORMED.match(_normalize(pin)))


def _index(pin: Union[str, int]) -> int:
    s = _normalize(pin)
    if not _WELL_FORMED.match(s):
        return -1
    target = int(s)
    pins = _load()["pins"]
    i = bisect_left(pins, target)
    if i < len(pins) and pins[i] == target:
        return i
    return -1


def validate(pin: Union[str, int]) -> bool:
    """True only if the pincode exists in the dataset (not merely well-formed)."""
    return _index(pin) != -1


def _district_ids(group) -> List[int]:
    return group if isinstance(group, list) else [group]


def get_details(pin: Union[str, int]) -> Optional[PincodeDetails]:
    i = _index(pin)
    if i == -1:
        return None
    d = _load()
    si = d["state_idx"][i]
    ids = _district_ids(d["district_groups"][i])
    return {
        "pincode": f"{d['pins'][i]:06d}",
        "state": None if si == -1 else d["states"][si],
        "state_source": d["state_sources"][d["state_source_idx"][i]],
        "districts": [d["districts"][x] for x in ids],
    }


def get_state(pin: Union[str, int]) -> Optional[str]:
    details = get_details(pin)
    return details["state"] if details else None


def get_districts(pin: Union[str, int]) -> List[str]:
    details = get_details(pin)
    return details["districts"] if details else []


def list_states() -> List[str]:
    return list(_load()["states"])


def list_districts(state: str) -> List[str]:
    d = _load()
    target = str(state).strip().upper()
    try:
        si = d["states"].index(target)
    except ValueError:
        return []
    out = set()
    for i, s in enumerate(d["state_idx"]):
        if s != si:
            continue
        for x in _district_ids(d["district_groups"][i]):
            out.add(d["districts"][x])
    return sorted(out)


def get_pincodes(state: Optional[str] = None, district: Optional[str] = None) -> List[str]:
    """Pincodes filtered by state and/or district."""
    d = _load()
    si = -1
    if state is not None:
        try:
            si = d["states"].index(str(state).strip().upper())
        except ValueError:
            return []
    di = -1
    if district is not None:
        try:
            di = d["districts"].index(str(district).strip().upper())
        except ValueError:
            return []
    out = []
    for i, pin in enumerate(d["pins"]):
        if si != -1 and d["state_idx"][i] != si:
            continue
        if di != -1 and di not in _district_ids(d["district_groups"][i]):
            continue
        out.append(f"{pin:06d}")
    return out


def __getattr__(name: str):
    # Lazily expose DATA_VERSION without forcing a data load at import time.
    if name == "DATA_VERSION":
        return _load()["version"]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# ---- geo entry points: clear error unless the geo package is installed ------

_GEO_MSG = (
    "Post office / geo data is not available in the core package. Install "
    "indian-pincode[geo] (pip) / @devzoy/indian-pincode-geo (npm) for lookup, "
    "find_nearby, reverse_lookup, and get_centroid."
)


def _need_geo(*_args, **_kwargs):
    raise ImportError(_GEO_MSG)


lookup = _need_geo
find_nearby = _need_geo
reverse_lookup = _need_geo
get_centroid = _need_geo


# ---- v1 backward-compatibility shims (emit DeprecationWarning) --------------

def search_districts(query: str, fuzzy: bool = True) -> List[str]:
    """Deprecated (v1). Search district names by substring/exact match.

    Prefer list_districts(state) / get_pincodes(district=...) in v2.
    """
    import warnings
    warnings.warn(
        "search_districts() is deprecated; use list_districts(state) or "
        "get_pincodes(district=...) instead.",
        DeprecationWarning, stacklevel=2,
    )
    q = str(query).strip().upper()
    if not q:
        return []
    d = _load()
    if fuzzy:
        return sorted(name for name in d["districts"] if q in name)
    return sorted(name for name in d["districts"] if name == q)
