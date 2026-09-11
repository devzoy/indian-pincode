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
    state: Optional[str]        # primary state (most offices; ties alphabetical)
    states: List[str]           # all states observed for the pincode, sorted
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
            "district_pairs": payload["districtPairs"],   # [ [districtNameIdx, stateIdx], ... ]
            "state_sources": payload["stateSources"],
            "pins": pins,
            "state_idx": payload["stateIdx"],
            "states_all_idx": payload["statesAllIdx"],
            "state_source_idx": payload["stateSourceIdx"],
            "pair_groups": payload["pairGroups"],
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


def _pair_ids(group) -> List[int]:
    return group if isinstance(group, list) else [group]


def get_details(pin: Union[str, int]) -> Optional[PincodeDetails]:
    i = _index(pin)
    if i == -1:
        return None
    d = _load()
    si = d["state_idx"][i]
    pids = _pair_ids(d["pair_groups"][i])
    district_names = sorted({d["districts"][d["district_pairs"][pid][0]] for pid in pids})
    states_all = sorted(d["states"][s] for s in d["states_all_idx"][i])
    return {
        "pincode": f"{d['pins'][i]:06d}",
        "state": None if si == -1 else d["states"][si],
        "states": states_all,
        "state_source": d["state_sources"][d["state_source_idx"][i]],
        "districts": district_names,
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
    # Use only (state, district) pairs whose state matches.
    out = {d["districts"][d_idx] for (d_idx, s_idx) in d["district_pairs"] if s_idx == si}
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
    pairs = d["district_pairs"]
    out = []
    for i, pin in enumerate(d["pins"]):
        pids = _pair_ids(d["pair_groups"][i])
        ok = False
        if si == -1 and di == -1:
            ok = True
        else:
            for pid in pids:
                d_idx, s_idx = pairs[pid]
                if si != -1 and s_idx != si:
                    continue
                if di != -1 and d_idx != di:
                    continue
                ok = True
                break
            if not ok and di == -1 and si != -1 and si in d["states_all_idx"][i]:
                ok = True
        if ok:
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
