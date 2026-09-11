// Shared core logic. Pure ESM, no Node built-ins, so it works unchanged in
// browsers, bundlers, edge runtimes, and React Native. The data object is
// injected by the entry module (which imports the generated data module).

export function createCore(DATA) {
  let _decoded = null;

  function _decode() {
    if (_decoded) return _decoded;
    const { version, states, districts, districtPairs, stateSources,
      stateSourceDefault, pincodes, stateIdx, statesAllSparse, stateSourceSparse,
      pairGroups } = DATA;
    const pins = new Array(pincodes.length);
    let acc = 0;
    for (let i = 0; i < pincodes.length; i++) {
      acc += pincodes[i];
      pins[i] = acc;
    }
    _decoded = { version, states, districts, districtPairs, stateSources,
      stateSourceDefault, pins, stateIdx, statesAllSparse, stateSourceSparse,
      pairGroups };
    return _decoded;
  }

  // all state ids for pincode index i (sparse: [stateIdx] unless multi-state)
  function _statesAll(i) {
    const d = _decoded;
    const explicit = d.statesAllSparse[i];
    if (explicit) return explicit;
    return d.stateIdx[i] === -1 ? [] : [d.stateIdx[i]];
  }

  // state-source code for pincode index i (sparse: default unless overridden)
  function _stateSourceCode(i) {
    const d = _decoded;
    const v = d.stateSourceSparse[i];
    return v === undefined ? d.stateSourceDefault : v;
  }

  // districtPairs[pid] = [districtNameIdx, stateIdx]
  function _pairIds(grp) {
    return Array.isArray(grp) ? grp : [grp];
  }

  function preload() {
    _decode();
  }

  const WELL_FORMED = /^[1-9][0-9]{5}$/;

  function _normalize(pin) {
    return String(pin).trim();
  }

  function isWellFormed(pin) {
    return WELL_FORMED.test(_normalize(pin));
  }

  function _index(pin) {
    const s = _normalize(pin);
    if (!WELL_FORMED.test(s)) return -1;
    const target = parseInt(s, 10);
    const { pins } = _decode();
    let lo = 0;
    let hi = pins.length - 1;
    while (lo <= hi) {
      const mid = (lo + hi) >> 1;
      const v = pins[mid];
      if (v === target) return mid;
      if (v < target) lo = mid + 1;
      else hi = mid - 1;
    }
    return -1;
  }

  function validate(pin) {
    return _index(pin) !== -1;
  }

  function _pinStr(n) {
    return String(n).padStart(6, '0');
  }

  function getDetails(pin) {
    const i = _index(pin);
    if (i === -1) return null;
    const d = _decode();
    const si = d.stateIdx[i];
    const pids = _pairIds(d.pairGroups[i]);
    // districts (names only), de-duplicated and sorted
    const districtNames = Array.from(
      new Set(pids.map((pid) => d.districts[d.districtPairs[pid][0]]))
    ).sort();
    const statesAll = _statesAll(i).map((s) => d.states[s]).sort();
    return {
      pincode: _pinStr(d.pins[i]),
      state: si === -1 ? null : d.states[si],   // primary (most offices; ties alpha)
      states: statesAll,                        // all states observed, sorted
      stateSource: d.stateSources[_stateSourceCode(i)],
      districts: districtNames,
    };
  }

  function getState(pin) {
    const details = getDetails(pin);
    return details ? details.state : null;
  }

  function getDistricts(pin) {
    const details = getDetails(pin);
    return details ? details.districts : [];
  }

  function listStates() {
    return _decode().states.slice();
  }

  function listDistricts(state) {
    const d = _decode();
    const target = String(state).trim().toUpperCase();
    const si = d.states.indexOf(target);
    if (si === -1) return [];
    // Use only (state, district) pairs whose state matches the requested state.
    const out = new Set();
    for (const [dNameIdx, sIdx] of d.districtPairs) {
      if (sIdx === si) out.add(d.districts[dNameIdx]);
    }
    return Array.from(out).sort();
  }

  function getPincodes(filter) {
    const { state, district } = filter || {};
    const d = _decode();
    const si = state == null ? -1 : d.states.indexOf(String(state).trim().toUpperCase());
    if (state != null && si === -1) return [];
    let di = -1;
    if (district != null) {
      di = d.districts.indexOf(String(district).trim().toUpperCase());
      if (di === -1) return [];
    }
    const out = [];
    for (let i = 0; i < d.pins.length; i++) {
      // Filter on any (state, district) pair that satisfies BOTH constraints
      // (so state+district only matches when they co-occur on the same pincode).
      const pids = _pairIds(d.pairGroups[i]);
      let ok = false;
      if (si === -1 && di === -1) {
        ok = true;
      } else {
        for (const pid of pids) {
          const [dNameIdx, sIdx] = d.districtPairs[pid];
          if (si !== -1 && sIdx !== si) continue;
          if (di !== -1 && dNameIdx !== di) continue;
          ok = true;
          break;
        }
        // state-only filter with a pincode that has no district pairs: fall back
        // to the primary/observed states.
        if (!ok && di === -1 && si !== -1) {
          if (_statesAll(i).includes(si)) ok = true;
        }
      }
      if (ok) out.push(_pinStr(d.pins[i]));
    }
    return out;
  }

  function _needGeo() {
    throw new Error(
      'Post office / geo data is not available in the core package. Install ' +
      '@devzoy/indian-pincode-geo (npm) / indian-pincode[geo] (pip) for lookup, ' +
      'findNearby, reverseLookup, and getCentroid.'
    );
  }

  // ---- v1 backward-compatibility shims (warn once) ----
  let _warnedSearchDistricts = false;
  function searchDistricts(query, fuzzy = true) {
    if (!_warnedSearchDistricts) {
      _warnedSearchDistricts = true;
      console.warn('[indian-pincode] searchDistricts() is deprecated; use ' +
        'listDistricts(state) or getPincodes({ district }) instead.');
    }
    const q = String(query).trim().toUpperCase();
    if (!q) return [];
    const d = _decode();
    return fuzzy
      ? d.districts.filter((name) => name.includes(q)).sort()
      : d.districts.filter((name) => name === q).sort();
  }

  return {
    validate,
    isWellFormed,
    getDetails,
    getState,
    getDistricts,
    listStates,
    listDistricts,
    getPincodes,
    preload,
    DATA_VERSION: DATA.version,
    lookup: _needGeo,
    findNearby: _needGeo,
    reverseLookup: _needGeo,
    getCentroid: _needGeo,
    searchDistricts, // deprecated v1 alias
    _decode,
  };
}
