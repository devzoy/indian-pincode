import { test } from 'node:test';
import assert from 'node:assert/strict';
import { loadCore, loadGeo } from './_helpers.mjs';

const core = await loadCore();
const geo = await loadGeo();

test('validate rejects malformed pincodes', () => {
  for (const bad of ['000000', '012345', '12345', '1234567', 'abcdef', '']) {
    assert.equal(core.validate(bad), false, bad);
    assert.equal(core.getDetails(bad), null, bad);
  }
});

test('validate handles null/undefined/float', () => {
  assert.equal(core.validate(null), false);
  assert.equal(core.validate(undefined), false);
  assert.equal(core.validate(110001.0), true);   // 110001.0 -> "110001"
  assert.equal(core.validate(110001.5), false);  // "110001.5" not 6 digits
});

test('isWellFormed vs validate', () => {
  assert.equal(core.isWellFormed('999999'), true);
  assert.equal(core.validate('999999'), false);   // well-formed but not in dataset
  assert.equal(core.isWellFormed('012345'), false); // leading zero
});

test('validate accepts int and trims whitespace', () => {
  assert.equal(core.validate(110001), true);
  assert.equal(core.validate('  110001  '), true);
});

test('findNearby invalid coords and radius', () => {
  assert.throws(() => geo.findNearby(NaN, 77), TypeError);
  assert.throws(() => geo.findNearby('28', 77), TypeError);
  assert.throws(() => geo.findNearby(-91, 77), RangeError);
  assert.throws(() => geo.findNearby(28, 181), RangeError);
  assert.throws(() => geo.findNearby(28.6, 77.2, { radiusKm: -5 }), RangeError);
});

test('lookup/getCentroid unknown returns empty/null', () => {
  assert.deepEqual(geo.lookup('999999'), []);
  assert.equal(geo.getCentroid('999999'), null);
});
