import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { gunzipSync } from 'node:zlib';
import { join } from 'node:path';
import { loadGeo, REPO_ROOT } from './_helpers.mjs';

const geo = await loadGeo();

// Load the raw geo records (int32 coords) for a brute-force reference.
const recordsPath = join(REPO_ROOT, 'packages', 'node-geo', 'data', 'records.json.gz');
const data = JSON.parse(gunzipSync(readFileSync(recordsPath)).toString('utf8'));
const scale = data.scale;

function toRad(v) { return (v * Math.PI) / 180; }
function haversineKm(la1, lo1, la2, lo2) {
  const R = 6371;
  const dLat = toRad(la2 - la1);
  const dLon = toRad(lo2 - lo1);
  const a = Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(la1)) * Math.cos(toRad(la2)) * Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function brute(lat, lon, radiusKm, includeSuspect) {
  const out = [];
  for (const row of data.records) {
    if (row[6] === null) continue;                 // no coords
    if (row[8] === 2 && !includeSuspect) continue;  // suspect
    const d = haversineKm(lat, lon, row[6] / scale, row[7] / scale);
    if (d <= radiusKm) out.push(`${row[0]}|${row[1]}`);
  }
  return out.sort();
}

// deterministic RNG
function makeRng(seed) {
  let s = seed >>> 0;
  return () => { s = (s * 1103515245 + 12345) & 0x7fffffff; return s / 0x7fffffff; };
}

for (const includeSuspect of [false, true]) {
  test(`findNearby == brute force on 500 points (includeSuspect=${includeSuspect})`, () => {
    const rng = makeRng(includeSuspect ? 99 : 7);
    let checked = 0;
    for (let i = 0; i < 500; i++) {
      const lat = 6.5 + rng() * 31;
      const lon = 68 + rng() * 29.5;
      const got = geo.findNearby(lat, lon, { radiusKm: 5, limit: 1000000, includeSuspect })
        .map((o) => `${o.pincode}|${o.officeName}`).sort();
      const expected = brute(lat, lon, 5, includeSuspect);
      assert.deepEqual(got, expected, `mismatch at ${lat},${lon}`);
      checked++;
    }
    assert.equal(checked, 500);
  });
}

test('findNearby rejects invalid coordinates', () => {
  assert.throws(() => geo.findNearby(NaN, 77), TypeError);
  assert.throws(() => geo.findNearby(28, 'x'), TypeError);
  assert.throws(() => geo.findNearby(200, 77), RangeError);
  assert.throws(() => geo.findNearby(28, 400), RangeError);
});

// Regression test for a box-search bug: an expanding-box nearest-neighbor search
// that stops at the first non-empty box can return the wrong pincode -- a closer
// point can sit just outside the box, near a corner. Perturbs points near real
// centroids (not uniform random ones) since that's exactly where the corner-miss
// bug bites: right at the boundary between two pincodes' areas of influence.
const centroidsPath = join(REPO_ROOT, 'packages', 'node-geo', 'data', 'centroids.json.gz');
const centroidData = JSON.parse(gunzipSync(readFileSync(centroidsPath)).toString('utf8'));
const centroidScale = centroidData.scale;
const centroidList = Object.entries(centroidData.centroids)
  .map(([pincode, [lat, lon]]) => [pincode, lat / centroidScale, lon / centroidScale]);

function bruteNearest(lat, lon) {
  let bestPin = null, bestDist = Infinity;
  for (const [pincode, plat, plon] of centroidList) {
    const d = haversineKm(lat, lon, plat, plon);
    if (d < bestDist) { bestDist = d; bestPin = pincode; }
  }
  return { pincode: bestPin, distanceKm: bestDist };
}

test('reverseLookup == brute force near 2000 real centroids', () => {
  const rng = makeRng(2024);
  const n = Math.min(2000, centroidList.length);
  const mismatches = [];
  for (let i = 0; i < n; i++) {
    const idx = Math.floor(rng() * centroidList.length);
    const [, lat, lon] = centroidList[idx];
    const jlat = lat + (rng() * 2 - 1) * 0.02;
    const jlon = lon + (rng() * 2 - 1) * 0.02;
    const got = geo.reverseLookup(jlat, jlon);
    const expected = bruteNearest(jlat, jlon);
    if (!got || got.pincode !== expected.pincode) {
      if (got && Math.abs(got.distanceKm - expected.distanceKm) < 0.001) continue; // genuine tie
      mismatches.push({ jlat, jlon, got, expected });
    }
  }
  assert.equal(mismatches.length, 0, `mismatches: ${JSON.stringify(mismatches.slice(0, 5))}`);
});

test('reverseLookup maxKm', () => {
  assert.ok(geo.reverseLookup(28.6304, 77.2177, 1) !== null);
  assert.equal(geo.reverseLookup(15.0, 68.0, 1), null);
  assert.throws(() => geo.reverseLookup(28.6, 77.2, -1), RangeError);
});
