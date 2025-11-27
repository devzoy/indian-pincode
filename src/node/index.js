const fs = require('fs');
const path = require('path');

const DATA_DIR = path.join(__dirname, 'data');
const COMPRESSED_JSON = path.join(DATA_DIR, 'pincodes.compressed.json');
const DISTRICTS_JSON = path.join(DATA_DIR, 'districts.json');
const GEO_JSON = path.join(DATA_DIR, 'geo.json');

// Lazy loaded data
let validationData = null;
let districtsData = null;
let geoData = null;

function loadValidationData() {
    if (!validationData) {
        validationData = JSON.parse(fs.readFileSync(COMPRESSED_JSON, 'utf8'));
    }
    return validationData;
}

function loadDistrictsData() {
    if (!districtsData) {
        districtsData = JSON.parse(fs.readFileSync(DISTRICTS_JSON, 'utf8'));
    }
    return districtsData;
}

function loadGeoData() {
    if (!geoData) {
        geoData = JSON.parse(fs.readFileSync(GEO_JSON, 'utf8'));
    }
    return geoData;
}

/**
 * Validate a pincode.
 * @param {string|number} pincode 
 * @returns {boolean}
 */
function validate(pincode) {
    const code = String(pincode).trim();
    if (code.length !== 6 || isNaN(code)) return false;

    const prefix = code.substring(0, 3);
    const suffix = parseInt(code.substring(3), 10);

    const data = loadValidationData();
    if (data[prefix]) {
        // Check if suffix exists in the sorted array
        // Using simple includes for now, could be binary search
        return data[prefix].includes(suffix);
    }
    return false;
}

/**
 * Lookup details for a pincode.
 * @param {string|number} pincode 
 * @returns {Promise<Array>} List of office details
 */
function lookup(pincode) {
    return new Promise((resolve, reject) => {
        const code = String(pincode).trim();
        if (!validate(code)) {
            return resolve([]);
        }

        const prefix = code.substring(0, 3);
        const chunkPath = path.join(DATA_DIR, 'details', `${prefix}.json`);

        fs.readFile(chunkPath, 'utf8', (err, data) => {
            if (err) {
                // If file doesn't exist (shouldn't happen if valid), return empty
                return resolve([]);
            }
            try {
                const chunk = JSON.parse(data);
                resolve(chunk[code] || []);
            } catch (e) {
                reject(e);
            }
        });
    });
}

/**
 * Search for districts.
 * @param {string} query 
 * @param {boolean} fuzzy 
 * @returns {Array<string>}
 */
function searchDistricts(query, fuzzy = true) {
    const q = query.trim().toLowerCase();
    if (!q) return [];

    const districts = loadDistrictsData();
    if (fuzzy) {
        return districts.filter(d => d.toLowerCase().includes(q));
    } else {
        return districts.filter(d => d.toLowerCase() === q);
    }
}

function toRad(Value) {
    return Value * Math.PI / 180;
}

function calcDistance(lat1, lon1, lat2, lon2) {
    const R = 6371; // km
    const dLat = toRad(lat2 - lat1);
    const dLon = toRad(lon2 - lon1);
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
        Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
        Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
}

/**
 * Find pincodes nearby a coordinate.
 * @param {number} lat 
 * @param {number} lng 
 * @param {number} radiusKm 
 * @returns {Promise<Array>}
 */
async function findNearby(lat, lng, radiusKm = 5) {
    const points = loadGeoData();
    const nearby = [];

    // 1. Filter points
    for (const point of points) {
        const [p, pLat, pLng] = point;
        const dist = calcDistance(lat, lng, pLat, pLng);
        if (dist <= radiusKm) {
            nearby.push({ pincode: String(p), distance: parseFloat(dist.toFixed(2)) });
        }
    }

    nearby.sort((a, b) => a.distance - b.distance);

    // 2. Fetch details for each (optional, but useful)
    // The user might just want pincodes, but usually details.
    // Let's return the basic info + distance.
    // If they want full details, they can call lookup.
    // But wait, the Python version returns full details.
    // Let's try to fetch details for the top results.

    const results = [];
    for (const item of nearby) {
        const details = await lookup(item.pincode);
        // Attach distance and pincode to each office
        details.forEach(d => {
            d.distance = item.distance;
            d.pincode = item.pincode;
        });
        results.push(...details);
    }

    return results;
}

/**
 * Search for all pincodes in a district.
 * @param {string} districtName 
 * @returns {Promise<Array>} List of pincodes in the district
 */
async function searchByDistrict(districtName) {
    const query = districtName.trim().toUpperCase();
    if (!query) return [];

    const allPincodes = loadValidationData();
    const results = [];

    // Load all detail chunks and search for matching district
    for (const prefix in allPincodes) {
        const chunkPath = path.join(DATA_DIR, 'details', `${prefix}.json`);
        try {
            const data = fs.readFileSync(chunkPath, 'utf8');
            const chunk = JSON.parse(data);

            for (const pincode in chunk) {
                const offices = chunk[pincode];
                // Check if any office in this pincode matches the district
                const hasMatch = offices.some(office =>
                    office.district && office.district.toUpperCase().includes(query)
                );

                if (hasMatch) {
                    results.push(...offices.map(office => ({
                        pincode: pincode,
                        office: office.office,
                        district: office.district,
                        state: office.state,
                        latitude: office.latitude,
                        longitude: office.longitude
                    })));
                }
            }
        } catch (err) {
            // Skip if file doesn't exist or can't be read
            continue;
        }
    }

    return results;
}

module.exports = {
    validate,
    lookup,
    searchDistricts,
    searchByDistrict,
    findNearby
};
