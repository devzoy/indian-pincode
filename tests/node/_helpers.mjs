// Shared helpers for Node tests. Resolves the built core + geo packages and maps
// the neutral snake_case golden values to Node's camelCase keys.
import { readFileSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { dirname, join } from 'node:path';

export const REPO_ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');

export async function loadCore() {
  return import(pathToFileURL(join(REPO_ROOT, 'packages', 'node-core', 'dist', 'index.mjs')));
}

export async function loadGeo() {
  return import(pathToFileURL(join(REPO_ROOT, 'packages', 'node-geo', 'dist', 'index.mjs')));
}

export function loadGolden() {
  return JSON.parse(
    readFileSync(join(REPO_ROOT, 'tests', 'fixtures', 'golden.json'), 'utf8')
  );
}

// Neutral (snake_case) core entry -> Node camelCase shape.
export function coreExpectedToNode(c) {
  return {
    pincode: c.pincode,
    state: c.state,
    states: c.states,
    stateSource: c.state_source,
    districts: c.districts,
  };
}

// Neutral geo office -> Node camelCase shape (coordinates handled by caller).
export function geoOfficeToNode(o) {
  return {
    pincode: o.pincode,
    officeName: o.office_name,
    officeType: o.office_type,
    deliveryStatus: o.delivery_status,
    district: o.district,
    state: o.state,
    stateSource: o.state_source,
    geoQuality: o.geo_quality,
    latitude: o.latitude,
    longitude: o.longitude,
  };
}
