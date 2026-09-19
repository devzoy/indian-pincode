/** indian-pincode core: validation + pincode -> state/district(s). */

export interface PincodeDetails {
  /** The 6-digit pincode. */
  pincode: string;
  /** Primary state/UT (most offices; ties alphabetical), or null if unknown. */
  state: string | null;
  /** All states the pincode touches, sorted (one entry unless cross-state). */
  states: string[];
  /** How the primary state was determined. */
  stateSource: 'source' | 'inferred_pincode' | 'inferred_circle' | 'null';
  /** District names (UPPERCASE); may contain more than one, or be empty. */
  districts: string[];
}

export interface GetPincodesFilter {
  state?: string;
  district?: string;
}

/** True only if the pincode exists in the dataset (not merely well-formed). */
export function validate(pin: string | number): boolean;

/** Format-only check: 6 digits, no leading zero. Does not check existence. */
export function isWellFormed(pin: string | number): boolean;

/** Details for a pincode, or null if it does not exist. */
export function getDetails(pin: string | number): PincodeDetails | null;

/** State/UT name for a pincode, or null. */
export function getState(pin: string | number): string | null;

/** District names for a pincode (possibly empty). */
export function getDistricts(pin: string | number): string[];

/** All state/UT names, sorted. */
export function listStates(): string[];

/** District names within a state, sorted. */
export function listDistricts(state: string): string[];

/** Pincodes filtered by state and/or district. */
export function getPincodes(filter?: GetPincodesFilter): string[];

/** Eagerly load and decode the dataset (optional; the library is lazy). */
export function preload(): void;

/** The data snapshot version (YYYY.MM.DD). */
export const DATA_VERSION: string;

/** @deprecated v1 alias. Use listDistricts(state) or getPincodes({ district }). */
export function searchDistricts(query: string, fuzzy?: boolean): string[];

// Geo entry points. These throw a clear install error in the core package;
// installing @devzoy/indian-pincode-geo provides working implementations.
export function lookup(pin: string | number): never;
export function findNearby(lat: number, lon: number, opts?: unknown): never;
export function reverseLookup(lat: number, lon: number): never;
export function getCentroid(pin: string | number): never;

declare const _default: {
  validate: typeof validate;
  isWellFormed: typeof isWellFormed;
  getDetails: typeof getDetails;
  getState: typeof getState;
  getDistricts: typeof getDistricts;
  listStates: typeof listStates;
  listDistricts: typeof listDistricts;
  getPincodes: typeof getPincodes;
  preload: typeof preload;
  DATA_VERSION: string;
  searchDistricts: typeof searchDistricts;
  lookup: typeof lookup;
  findNearby: typeof findNearby;
  reverseLookup: typeof reverseLookup;
  getCentroid: typeof getCentroid;
};
export default _default;
