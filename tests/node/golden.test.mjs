import { test } from 'node:test';
import assert from 'node:assert/strict';
import { loadCore, loadGeo, loadGolden, coreExpectedToNode, geoOfficeToNode } from './_helpers.mjs';

const core = await loadCore();
const geo = await loadGeo();
const golden = loadGolden();

test('golden fixture present and matches data version', () => {
  assert.ok(golden.count >= 200);
  assert.equal(golden.data_version, core.DATA_VERSION);
});

test('core getDetails matches golden (all entries)', () => {
  for (const e of golden.entries) {
    const exp = coreExpectedToNode(e.core);
    const got = core.getDetails(e.pincode);
    assert.ok(got, `${e.pincode} not found`);
    assert.equal(got.pincode, exp.pincode);
    assert.equal(got.state, exp.state);
    assert.deepEqual(got.states, exp.states);
    assert.equal(got.stateSource, exp.stateSource);
    assert.deepEqual(got.districts, exp.districts);
    assert.equal(core.validate(e.pincode), true);
  }
});

test('geo lookup matches golden (all entries)', () => {
  for (const e of golden.entries) {
    const got = geo.lookup(e.pincode);
    assert.equal(got.length, e.geo.length, `${e.pincode} office count`);
    for (let i = 0; i < got.length; i++) {
      const g = got[i];
      const x = geoOfficeToNode(e.geo[i]);
      for (const k of ['pincode', 'officeName', 'officeType', 'deliveryStatus',
        'district', 'state', 'stateSource', 'geoQuality']) {
        assert.equal(g[k], x[k], `${e.pincode} ${k}`);
      }
      for (const k of ['latitude', 'longitude']) {
        if (x[k] === null) assert.equal(g[k], null);
        else assert.ok(Math.abs(g[k] - x[k]) < 1e-4, `${e.pincode} ${k}`);
      }
    }
  }
});
