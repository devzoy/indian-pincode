# indian-pincode (core)

Offline-first Indian pincode validation and pincode → state/district lookup.
No runtime network calls. For post offices and geospatial search, install the geo
extra: `pip install indian-pincode[geo]`.

```python
import indian_pincode as pincode

pincode.validate("110001")          # True (exists in dataset)
pincode.is_well_formed("999999")    # True (format only)
pincode.get_details("110001")       # {'pincode': '110001', 'state': 'DELHI', 'districts': ['NEW DELHI']}
pincode.get_state("560001")         # 'KARNATAKA'
pincode.list_states()               # [...]
pincode.get_pincodes(state="GOA")   # [...]
pincode.DATA_VERSION                 # 'YYYY.MM.DD'
```

Data: derived from India Post / data.gov.in under GODL-India (attribution required).
See DATA_LICENSE.md. Code: MIT.
