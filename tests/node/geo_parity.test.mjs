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
