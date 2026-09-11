// Geo logic (ESM). Node-only: uses node:fs to lazily load data shards from the
// package's data/ directory (kept external, not bundled). Coordinates are int32
// at 1e-5 degrees.
import { readFileSync } from 'node:fs';
import { gunzipSync } from 'node:zlib';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

// Resolve the directory of the built module in a way that works in BOTH the ESM
// and CJS bundles esbuild produces. In ESM, import.meta.url is set; in the CJS
// bundle it is empty, so we fall back to __dirname (which esbuild provides).
function _here() {
  try {
    if (typeof import.meta !== 'undefined' && import.meta.url) {
      return dirname(fileURLToPath(import.meta.url));
    }
  } catch (_e) { /* import.meta not available in CJS */ }
  // eslint-disable-next-line no-undef
  return __dirname;
}

const DATA_DIR = join(_here(), '..', 'data');

let _records = null;
let _grid = null;
let _cent = null;
let _centGrid = null;
let _pinIndex = null; // pincode -> [record idx,...]

function _readJsonGz(name) {
  return JSON.parse(gunzipSync(readFileSync(join(DATA_DIR, name))).toString('utf8'));
}
function _loadRecords() {
  if (!_records) _records = _readJsonGz('records.json.gz');
  return _records;
}
function _loadGrid() {
  if (!_grid) _grid = _readJsonGz('grid.json.gz');
  return _grid;
}
function _loadCentroids() {
  if (!_cent) _cent = _readJsonGz('centroids.json.gz');
  return _cent;
}

const TYPE_ORDER = { HO: 0, PO: 1, BO: 2 };
const TYPE_NAME = ['HO', 'PO', 'BO'];
const DELIVERY_NAME = ['Non Delivery', 'Delivery'];

function _rowToObject(row, data) {
  const scale = data.scale;
  const [pincode, officeName, typeCode, delCode, districtId, stateId, lat, lon, gqCode, ssCode] = row;
  return {
    pincode,
    officeName,
    officeType: TYPE_NAME[typeCode] ?? String(typeCode),
    deliveryStatus: DELIVERY_NAME[delCode] ?? String(delCode),
    district: districtId === -1 ? null : data.districts[districtId],
    state: stateId === -1 ? null : data.states[stateId],
    stateSource: data.stateSources[ssCode] ?? String(ssCode),
    latitude: lat === null ? null : lat / scale,
    longitude: lon === null ? null : lon / scale,
    geoQuality: data.geoQuality[gqCode] ?? String(gqCode),
  };
}

function _toRad(v) { return (v * Math.PI) / 180; }
function _haversineKm(lat1, lon1, lat2, lon2) {
  const R = 6371;
  const dLat = _toRad(lat2 - lat1);
  const dLon = _toRad(lon2 - lon1);
  const a = Math.sin(dLat / 2) ** 2 +
    Math.cos(_toRad(lat1)) * Math.cos(_toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function _validateCoords(lat, lon) {
  if (typeof lat !== 'number' || typeof lon !== 'number' ||
      Number.isNaN(lat) || Number.isNaN(lon)) {
    throw new TypeError('latitude and longitude must be numbers');
  }
  if (lat < -90 || lat > 90 || lon < -180 || lon > 180) {
    throw new RangeError('latitude/longitude out of range');
  }
}

export function preload() {
  _loadRecords();
  _loadGrid();
  _loadCentroids();
  _buildCentroidGrid();
  _pinIdx();
}

/** The geo data snapshot version (from records.json). */
export function dataVersion() {
  return _loadRecords().version;
}

let _versionChecked = false;
/** Warn once (non-fatal) if the installed core and geo data versions disagree. */
export function checkVersionAgainstCore(coreVersion) {
  if (_versionChecked) return;
  _versionChecked = true;
  try {
    const geoV = dataVersion();
    if (coreVersion && geoV && coreVersion !== geoV &&
        typeof process !== 'undefined' && process.emitWarning) {
      process.emitWarning(
        `@devzoy/indian-pincode core DATA_VERSION (${coreVersion}) != ` +
        `@devzoy/indian-pincode-geo data version (${geoV}). Install matching ` +
        'versions to avoid inconsistent results.',
        'IndianPincodeVersionMismatch'
      );
    }
  } catch (_e) { /* never let the check break usage */ }
}

function _pinIdx() {
  if (_pinIndex) return _pinIndex;
  const data = _loadRecords();
  const m = new Map();
  for (let i = 0; i < data.records.length; i++) {
    const p = data.records[i][0];
    let arr = m.get(p);
    if (!arr) { arr = []; m.set(p, arr); }
    arr.push(i);
  }
  _pinIndex = m;
  return _pinIndex;
}

export function lookup(pin) {
  const s = String(pin).trim();
  const data = _loadRecords();
  const idxs = _pinIdx().get(s);
  if (!idxs) return [];
  const out = idxs.map((i) => _rowToObject(data.records[i], data));
  // Records are pre-sorted (HO, PO, BO, office name) at emit time; sort again
  // defensively.
  // Sort by office type (HO, PO, BO) then office name by CODE POINT (not locale),
  // matching the pipeline's Python sort so Node and Python return identical order.
  out.sort((a, b) =>
    (TYPE_ORDER[a.officeType] ?? 9) - (TYPE_ORDER[b.officeType] ?? 9) ||
    (a.officeName < b.officeName ? -1 : a.officeName > b.officeName ? 1 : 0));
  return out;
}

export function findNearby(lat, lon, opts) {
  _validateCoords(lat, lon);
  const { radiusKm = 5, limit = 20, includeSuspect = false } = opts || {};
  if (typeof radiusKm !== 'number' || Number.isNaN(radiusKm) || radiusKm < 0) {
    throw new RangeError('radiusKm must be a non-negative number');
  }
  const data = _loadRecords();
  const grid = _loadGrid();
  const scale = data.scale;
  const gridDeg = grid.gridDeg;

  const latSpan = radiusKm / 111.0 / gridDeg;
  const lonSpan = radiusKm / (111.0 * Math.max(0.01, Math.cos(_toRad(lat)))) / gridDeg;
  const latCell = Math.floor(lat / gridDeg);
  const lonCell = Math.floor(lon / gridDeg);
  const latR = Math.ceil(latSpan) + 1;
  const lonR = Math.ceil(lonSpan) + 1;

  const results = [];
  for (let dla = -latR; dla <= latR; dla++) {
    for (let dlo = -lonR; dlo <= lonR; dlo++) {
      const idxs = grid.cells[`${latCell + dla},${lonCell + dlo}`];
      if (!idxs) continue;
      for (const idx of idxs) {
        const row = data.records[idx];
        // geoQuality code index 2 == 'suspect'
        if (row[8] === 2 && !includeSuspect) continue;
        const dist = _haversineKm(lat, lon, row[6] / scale, row[7] / scale);
        if (dist <= radiusKm) {
          const obj = _rowToObject(row, data);
          obj.distanceKm = Math.round(dist * 1000) / 1000;
          results.push(obj);
        }
      }
    }
  }
  results.sort((a, b) => a.distanceKm - b.distanceKm);
  return typeof limit === 'number' && limit >= 0 ? results.slice(0, limit) : results;
}

function _buildCentroidGrid() {
  if (_centGrid) return _centGrid;
  const c = _loadCentroids();
  const grid = new Map();
  const gridDeg = 0.1;
  for (const pin in c.centroids) {
    const [lat, lon] = c.centroids[pin];
    const key = `${Math.floor((lat / c.scale) / gridDeg)},${Math.floor((lon / c.scale) / gridDeg)}`;
    if (!grid.has(key)) grid.set(key, []);
    grid.get(key).push(pin);
  }
  _centGrid = { grid, gridDeg, scale: c.scale };
  return _centGrid;
}

export function reverseLookup(lat, lon) {
  _validateCoords(lat, lon);
  const c = _loadCentroids();
  const cg = _buildCentroidGrid();
  const gridDeg = cg.gridDeg;
  const latCell = Math.floor(lat / gridDeg);
  const lonCell = Math.floor(lon / gridDeg);

  let best = null;
  for (let ring = 1; ring <= 60; ring++) {
    for (let dla = -ring; dla <= ring; dla++) {
      for (let dlo = -ring; dlo <= ring; dlo++) {
        if (ring > 1 && Math.abs(dla) !== ring && Math.abs(dlo) !== ring) continue;
        const pins = cg.grid.get(`${latCell + dla},${lonCell + dlo}`);
        if (!pins) continue;
        for (const pin of pins) {
          const [plat, plon] = c.centroids[pin];
          const dist = _haversineKm(lat, lon, plat / c.scale, plon / c.scale);
          if (!best || dist < best.distanceKm) {
            best = { pincode: pin, distanceKm: Math.round(dist * 1000) / 1000 };
          }
        }
      }
    }
    if (best) break;
  }
  return best;
}

export function getCentroid(pin) {
  const s = String(pin).trim();
  const c = _loadCentroids();
  const v = c.centroids[s];
  if (!v) return null;
  return { latitude: v[0] / c.scale, longitude: v[1] / c.scale };
}
