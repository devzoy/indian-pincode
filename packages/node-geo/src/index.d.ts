/** indian-pincode-geo: post offices, coordinates, nearby search, reverse lookup. */

export type GeoQuality = 'original' | 'swapped' | 'suspect' | 'removed' | 'missing';

export interface PostOffice {
  pincode: string;
  officeName: string;
  officeType: 'HO' | 'PO' | 'BO';
  deliveryStatus: 'Delivery' | 'Non Delivery';
  district: string | null;
  state: string | null;
  stateSource: 'source' | 'inferred_pincode' | 'inferred_circle' | 'null';
  latitude: number | null;
  longitude: number | null;
  geoQuality: GeoQuality;
}

export interface NearbyPostOffice extends PostOffice {
  /** Great-circle distance from the query point, in km. */
  distanceKm: number;
}

export interface FindNearbyOptions {
  /** Search radius in km (default 5). */
  radiusKm?: number;
  /** Max results (default 20). */
  limit?: number;
  /** Include geoQuality="suspect" points (default false). */
  includeSuspect?: boolean;
}

export interface ReverseLookupResult {
  pincode: string;
  distanceKm: number;
}

export interface Centroid {
  latitude: number;
  longitude: number;
}

export interface PincodeDetails {
  pincode: string;
  state: string | null;
  states: string[];
  stateSource: 'source' | 'inferred_pincode' | 'inferred_circle' | 'null';
  districts: string[];
}

// ---- geo ----
export function lookup(pin: string | number): PostOffice[];
export function findNearby(lat: number, lon: number, opts?: FindNearbyOptions): NearbyPostOffice[];
export function reverseLookup(lat: number, lon: number): ReverseLookupResult | null;
export function getCentroid(pin: string | number): Centroid | null;

// ---- re-exported core ----
export function validate(pin: string | number): boolean;
export function isWellFormed(pin: string | number): boolean;
export function getDetails(pin: string | number): PincodeDetails | null;
export function getState(pin: string | number): string | null;
export function getDistricts(pin: string | number): string[];
export function listStates(): string[];
export function listDistricts(state: string): string[];
export function getPincodes(filter?: { state?: string; district?: string }): string[];
export const DATA_VERSION: string;

/** Eagerly load both core and geo data (optional). */
export function preload(): void;

declare const _default: {
  lookup: typeof lookup;
  findNearby: typeof findNearby;
  reverseLookup: typeof reverseLookup;
  getCentroid: typeof getCentroid;
  validate: typeof validate;
  isWellFormed: typeof isWellFormed;
  getDetails: typeof getDetails;
  getState: typeof getState;
  getDistricts: typeof getDistricts;
  listStates: typeof listStates;
  listDistricts: typeof listDistricts;
  getPincodes: typeof getPincodes;
  DATA_VERSION: string;
  preload: typeof preload;
};
export default _default;
