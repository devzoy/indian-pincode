// Shared core logic. Pure ESM, no Node built-ins, so it works unchanged in
// browsers, bundlers, edge runtimes, and React Native. The data object is
// injected by the entry module (which imports the generated data module).

export function createCore(DATA) {
  let _decoded = null;

  function _decode() {
    if (_decoded) return _decoded;
    const { version, states, districts, stateSources, pincodes, stateIdx,
      stateSourceIdx, districtGroups } = DATA;
    const pins = new Array(pincodes.length);
    let acc = 0;
    for (let i = 0; i < pincodes.length; i++) {
      acc += pincodes[i];
      pins[i] = acc;
    }
    _decoded = { version, states, districts, stateSources, pins, stateIdx,
      stateSourceIdx, districtGroups };
    return _decoded;
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
    const grp = d.districtGroups[i];
    const districtIds = Array.isArray(grp) ? grp : [grp];
    return {
      pincode: _pinStr(d.pins[i]),
      state: si === -1 ? null : d.states[si],
      stateSource: d.stateSources[d.stateSourceIdx[i]],
      districts: districtIds.map((id) => d.districts[id]),
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
    const out = new Set();
    for (let i = 0; i < d.pins.length; i++) {
      if (d.stateIdx[i] !== si) continue;
      const grp = d.districtGroups[i];
      const ids = Array.isArray(grp) ? grp : [grp];
      for (const id of ids) out.add(d.districts[id]);
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
      if (si !== -1 && d.stateIdx[i] !== si) continue;
      if (di !== -1) {
        const grp = d.districtGroups[i];
        const ids = Array.isArray(grp) ? grp : [grp];
        if (!ids.includes(di)) continue;
      }
      out.push(_pinStr(d.pins[i]));
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
