// Merged entry: re-exports the full core API plus working geo functions.
// Installing @devzoy/indian-pincode-geo gives you everything from
// @devzoy/indian-pincode (core) with lookup/findNearby/reverseLookup/getCentroid
// implemented (they throw in core alone).
import core from '@devzoy/indian-pincode';
import {
  lookup as geoLookup,
  findNearby as geoFindNearby,
  reverseLookup as geoReverseLookup,
  getCentroid as geoGetCentroid,
  preload as geoPreload,
  checkVersionAgainstCore,
} from './geo.mjs';

// Non-fatal, one-time check that the installed core and geo data agree. Runs
// lazily on first geo use rather than at import so it never touches the FS in a
// browser bundle where geo isn't actually invoked.
function _lazyVersionCheck() {
  try { checkVersionAgainstCore(core.DATA_VERSION); } catch (_e) { /* ignore */ }
}

// Core (re-exported)
export const validate = core.validate;
export const isWellFormed = core.isWellFormed;
export const getDetails = core.getDetails;
export const getState = core.getState;
export const getDistricts = core.getDistricts;
export const listStates = core.listStates;
export const listDistricts = core.listDistricts;
export const getPincodes = core.getPincodes;
export const DATA_VERSION = core.DATA_VERSION;
export const searchDistricts = core.searchDistricts; // deprecated v1 alias

// Geo (working implementations). Each triggers the one-time version check.
export function lookup(pin) { _lazyVersionCheck(); return geoLookup(pin); }
export function findNearby(lat, lon, opts) { _lazyVersionCheck(); return geoFindNearby(lat, lon, opts); }
export function reverseLookup(lat, lon) { _lazyVersionCheck(); return geoReverseLookup(lat, lon); }
export function getCentroid(pin) { _lazyVersionCheck(); return geoGetCentroid(pin); }

/** Eagerly load both core and geo data. */
export function preload() {
  core.preload();
  geoPreload();
  _lazyVersionCheck();
}

export default {
  validate, isWellFormed, getDetails, getState, getDistricts,
  listStates, listDistricts, getPincodes, DATA_VERSION, searchDistricts,
  lookup, findNearby, reverseLookup, getCentroid, preload,
};
