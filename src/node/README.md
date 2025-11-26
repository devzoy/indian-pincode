# Indian Pincode - Node.js Library

[![npm version](https://img.shields.io/npm/v/@devzoy/indian-pincode.svg)](https://www.npmjs.com/package/@devzoy/indian-pincode)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Node.js](https://img.shields.io/badge/Node.js-12%2B-green)](https://nodejs.org/)

**High-performance, offline-first Indian Pincode library for Node.js with zero external dependencies.**

## 🚀 Why Use This Library?

Most developers rely on external APIs for pincode lookups, which are slow, unreliable, and subject to rate limits. **Indian Pincode** embeds the entire dataset directly into your application with highly optimized indexing.

| Feature | External API | Indian Pincode Library |
| :--- | :--- | :--- |
| **Latency** | 200ms - 1000ms (Network dependent) | **< 1ms** (In-memory) |
| **Reliability** | Can go down, rate limits | **100% Uptime** (It's in your code) |
| **Privacy** | Sends user data to 3rd party | **Zero Data Leakage** (All local) |
| **Cost** | Often paid or freemium | **Free & Open Source** |
| **Offline** | No | **Yes** |

## 📦 Installation

```bash
npm install @devzoy/indian-pincode
```

Or with yarn:

```bash
yarn add @devzoy/indian-pincode
```

## 🔧 Usage

### Basic Examples

```javascript
const pincode = require('@devzoy/indian-pincode');

// 1. Validate a Pincode
console.log(pincode.validate("110001")); 
// Output: true

console.log(pincode.validate("999999")); 
// Output: false

// 2. Lookup Pincode Details
pincode.lookup("110001").then(details => {
    console.log(details[0].office);      // "Connaught Place SO"
    console.log(details[0].district);    // "NEW DELHI"
    console.log(details[0].state);       // "DELHI"
    console.log(details[0].latitude);    // 28.63
    console.log(details[0].longitude);   // 77.21
});

// 3. Find Nearby Post Offices (Geospatial Search)
// Find offices within 5km of coordinates (28.63, 77.21)
pincode.findNearby(28.63, 77.21, 5).then(results => {
    results.forEach(office => {
        console.log(`${office.pincode} - ${office.office} (${office.distance.toFixed(2)}km)`);
    });
});

// 4. Search by District
pincode.searchByDistrict("BANGALORE").then(results => {
    console.log(`Found ${results.length} pincodes in Bangalore`);
    console.log(results[0].pincode);  // "560001"
});
```

### Async/Await Style

```javascript
const pincode = require('@devzoy/indian-pincode');

async function getPincodeInfo(code) {
    try {
        const details = await pincode.lookup(code);
        if (details.length > 0) {
            console.log(`District: ${details[0].district}`);
            console.log(`State: ${details[0].state}`);
            console.log(`Offices: ${details.map(d => d.office).join(', ')}`);
        }
    } catch (error) {
        console.error('Error:', error);
    }
}

getPincodeInfo("560095");
```

## 📚 API Reference

### `validate(pincode)`

Validates if a pincode exists in the database.

**Parameters:**
- `pincode` (string): The 6-digit pincode to validate

**Returns:** `boolean`

**Example:**
```javascript
pincode.validate("110001");  // true
pincode.validate("000000");  // false
```

---

### `lookup(pincode)`

Retrieves detailed information for a given pincode.

**Parameters:**
- `pincode` (string): The 6-digit pincode to lookup

**Returns:** `Promise<Array>` - Array of office objects with the following properties:
- `pincode` (string): The pincode
- `office` (string): Post office name
- `district` (string): District name
- `state` (string): State name
- `latitude` (number): Latitude coordinate
- `longitude` (number): Longitude coordinate

**Example:**
```javascript
const details = await pincode.lookup("110001");
console.log(details[0].office);  // "Connaught Place SO"
```

---

### `findNearby(latitude, longitude, radiusKm = 10)`

Finds post offices within a specified radius of given coordinates.

**Parameters:**
- `latitude` (number): Latitude coordinate
- `longitude` (number): Longitude coordinate
- `radiusKm` (number, optional): Search radius in kilometers (default: 10)

**Returns:** `Promise<Array>` - Array of nearby offices sorted by distance, each with:
- All properties from `lookup()`
- `distance` (number): Distance in kilometers from the search point

**Example:**
```javascript
const nearby = await pincode.findNearby(28.63, 77.21, 5);
console.log(`${nearby[0].office} is ${nearby[0].distance.toFixed(2)}km away`);
```

---

### `searchByDistrict(districtName)`

Searches for all pincodes in a given district.

**Parameters:**
- `districtName` (string): District name (case-insensitive)

**Returns:** `Promise<Array>` - Array of all pincodes in the district

**Example:**
```javascript
const results = await pincode.searchByDistrict("BANGALORE");
console.log(results.length);  // Number of pincodes in Bangalore
```

## 🎯 Use Cases

- **E-commerce**: Auto-fill address forms, validate delivery locations
- **Logistics**: Calculate delivery zones, find nearest distribution centers
- **Real Estate**: Search properties by pincode, show nearby amenities
- **Government Apps**: Citizen services, location-based schemes
- **Analytics**: Geographic data analysis, demographic studies

## 🔍 Data Accuracy

Data is sourced and processed from official India Post records, covering:
- **19,000+** pincodes
- **154,000+** post offices
- All **28 states** and **8 union territories**
- Accurate **latitude/longitude** coordinates

## ⚡ Performance

- **Validation**: < 0.1ms (instant hash lookup)
- **Lookup**: < 1ms (lazy-loaded JSON chunks)
- **Geospatial Search**: < 10ms (optimized distance calculations)
- **Memory**: ~2MB (compressed data, loaded on-demand)

## 🛠 Technical Details

### Architecture
- **Pure JavaScript**: Zero external dependencies
- **Lazy Loading**: Data chunks loaded only when needed
- **Optimized Storage**: Compressed JSON with prefix-based chunking
- **Haversine Formula**: Accurate geospatial distance calculations

### Data Structure
```
data/
├── pincodes.compressed.json  # Main index (prefix → chunk mapping)
└── details/                  # Lazy-loaded detail chunks
    ├── 11.json              # All pincodes starting with "11"
    ├── 56.json              # All pincodes starting with "56"
    └── ...
```

## 🤝 Contributing

Contributions are welcome! Please see the [main repository](https://github.com/devzoy/indian-pincode) for contribution guidelines.

## 📄 License

MIT License - see [LICENSE](../../LICENSE) file for details.

## 🔗 Related Packages

- **Python**: `pip install indian-pincode`
- **Repository**: [github.com/devzoy/indian-pincode](https://github.com/devzoy/indian-pincode)

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/devzoy/indian-pincode/issues)
- **Email**: contact@devzoy.com

---

Made with ❤️ by [DevZoy](https://github.com/devzoy)
