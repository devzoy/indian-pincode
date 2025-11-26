# Indian Pincode 

**The Ultimate High-Performance, Offline-First Indian Pincode Library.**

<!-- [![CI](https://github.com/devzoy/india-pincode/workflows/CI/badge.svg)](https://github.com/devzoy/india-pincode/actions) -->
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.6%2B-blue)](https://www.python.org/)
[![Node.js](https://img.shields.io/badge/Node.js-12%2B-green)](https://nodejs.org/)

## 🚀 Why This is Better Than an API

Most developers rely on external APIs for pincode lookups. This is often slow, unreliable, and subject to rate limits. **Indian Pincode** solves this by embedding the entire dataset directly into your application with highly optimized indexing.

| Feature | External API | Indian Pincode Library |
| :--- | :--- | :--- |
| **Latency** | 200ms - 1000ms (Network dependent) | **< 1ms** (In-memory/Local DB) |
| **Reliability** | Can go down, rate limits | **100% Uptime** (It's in your code) |
| **Privacy** | Sends user location/query to 3rd party | **Zero Data Leakage** (All local) |
| **Cost** | Often paid or freemium | **Free & Open Source** |
| **Offline** | No | **Yes** |

## 📦 Libraries

We provide native, zero-dependency (where possible) libraries for the most popular backend languages.

### 🐍 Python
**Package**: `indian-pincode`
- **Backend**: SQLite (Embedded, Fast, Robust)
- **Installation**: `pip install src/python/` (Coming to PyPI as `indian-pincode`)

```python
import indian_pincode as pincode

# 1. Validate a Pincode
print(pincode.validate("110001")) 
# Output: True

# 2. Get Details (State, District, Office)
details = pincode.lookup("110001")
print(details[0]['office_name']) 
# Output: "Connaught Place SO"
print(details[0]['district'])    
# Output: "NEW DELHI"
print(details[0]['state_name'])  
# Output: "DELHI"

# 3. Geospatial Search (Find nearby post offices)
# Find offices within 5km of Connaught Place (28.63, 77.21)
nearby = pincode.find_nearby(28.63, 77.21, radius_km=5)
print(nearby[0]['pincode']) 
# Output: "110001"
```

### 🟢 Node.js
**Package**: `indian-pincode`
- **Backend**: Pure JavaScript with Optimized JSON Chunks (Lazy Loaded)
- **Installation**: `npm install ./src/node` (Coming to NPM as `@devzoy/indian-pincode`)

```javascript
const pincode = require('indian-pincode');

// 1. Validate
console.log(pincode.validate("560095")); 
// Output: true

// 2. Lookup
pincode.lookup("560095").then(details => {
    console.log(details[0].office);   
    // Output: "Koramangala VI Bk SO"
    console.log(details[0].district); 
    // Output: "BANGALORE"
});

// 3. Find Nearby
pincode.findNearby(12.93, 77.62).then(res => {
    console.log(res[0].pincode); 
    // Output: "560095"
});
```



## 🔍 Accuracy & Confidence

We source our data directly from processed official India Post records. Here are some examples of what you get:

**Query**: `110001`
**Result**:
- **District**: NEW DELHI
- **State**: DELHI
- **Offices**: Connaught Place SO, Parliament House SO, etc.

**Query**: `500081`
**Result**:
- **District**: HYDERABAD
- **State**: TELANGANA
- **Offices**: Madhapur SO, Cyberabad SO

**Query**: `700001`
**Result**:
- **District**: KOLKATA
- **State**: WEST BENGAL
- **Offices**: Kolkata GPO, Lalbazar SO

## 🛠 Contributing

We welcome contributions! Whether it's fixing a bug, adding a feature, or updating the data.

1.  **Fork** the repository.
2.  **Clone** your fork: `git clone https://github.com/YOUR_USERNAME/indian-pincode.git`
3.  **Create a Branch**: `git checkout -b feature/amazing-feature`
4.  **Commit** your changes: `git commit -m "Add amazing feature"`
5.  **Push** to the branch: `git push origin feature/amazing-feature`
6.  **Open a Pull Request**: Go to the original repository and click "New Pull Request".

### Data Updates
If you find missing or incorrect pincode data, please open an Issue with the details, or submit a PR updating the raw data processing scripts.

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

## 📊 Data Source

Data is processed from open government datasets provided by **India Post** (Department of Posts, Ministry of Communications, Government of India).
