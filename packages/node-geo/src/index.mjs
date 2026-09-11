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
} from './geo.mjs';

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

// Geo (working implementations)
export const lookup = geoLookup;
export const findNearby = geoFindNearby;
export const reverseLookup = geoReverseLookup;
export const getCentroid = geoGetCentroid;

/** Eagerly load both core and geo data. */
export function preload() {
  core.preload();
  geoPreload();
}

export default {
  validate, isWellFormed, getDetails, getState, getDistricts,
  listStates, listDistricts, getPincodes, DATA_VERSION, searchDistricts,
  lookup, findNearby, reverseLookup, getCentroid, preload,
};
