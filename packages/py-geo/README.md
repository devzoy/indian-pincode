# indian-pincode-geo

Geo companion for `indian-pincode`: post offices, coordinates, nearby search, and
reverse lookup. Offline, no runtime network calls. Depends on `indian-pincode`.

```python
import indian_pincode_geo as geo

geo.lookup("110001")                     # [{'pincode','officeName','officeType',...,'geoQuality'}, ...]
geo.find_nearby(28.63, 77.21, radius_km=5)   # [... {'distanceKm': ...}], excludes suspect by default
geo.find_nearby(28.63, 77.21, include_suspect=True)
geo.reverse_lookup(28.63, 77.21)         # {'pincode': '110001', 'distanceKm': ...}
geo.get_centroid("110001")               # {'latitude': ..., 'longitude': ...}
```

Importing this package also enables `indian_pincode.lookup(...)` etc.

Data: derived from India Post / data.gov.in under GODL-India (attribution required).
See DATA_LICENSE.md. Code: MIT.
