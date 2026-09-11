# Data Build Report

- **data_version:** `2025.11.26`
- **source_updated_date:** `2025-11-26`
- **source origin:** `local`  
- **source SHA-256:** `701ee84ba125a914e7ffc979c0308b3a041b8adffa85ec9d5f4e0579ecf062e5`
- **fetched_at:** `2026-09-11T11:37:21.044174+00:00`

## Counts

| Metric | Value |
| :--- | ---: |
| Input rows | 165627 |
| Invalid pincode rows dropped | 0 |
| Exact duplicate rows removed | 2 |
| Output post office rows | 165625 |
| Unique pincodes | 19586 |

## State backfill (NA rows)

| state_source | rows |
| :--- | ---: |
| inferred_circle | 18 |
| inferred_pincode | 609 |
| null | 88 |
| source | 164910 |

Backfill paths: inferred_pincode=609, inferred_circle=18, null=88.

## Coordinate cleaning

| Rule | Count |
| :--- | ---: |
| Both missing/NA/non-numeric -> null (missing) | 12006 |
| Partial (one of lat/lon null) -> null (missing) | 9 |
| In-box original | 150998 |
| Swapped (lon,lat) -> valid | 791 |
| Removed (out of box, swap did not help / garbage) | 1821 |
| Suspect via sibling-median rule | 12504 |
| Suspect via district-median fallback | 91 |

geo_quality distribution:

| geo_quality | rows |
| :--- | ---: |
| original | 138524 |
| swapped | 670 |
| suspect | 12595 |
| removed | 1821 |
| missing | 12015 |

## Outlier sanity check

Total suspect rows: 12595 (sibling rule: 12504, district fallback: 91).

**Sibling-distance distribution** (each office vs the median of its same-pincode siblings; n=141136). Current flag threshold: **50.0 km**.

| percentile | distance (km) |
| :--- | ---: |
| p50 | 5.67 |
| p75 | 13.21 |
| p90 | 43.24 |
| p95 | 97.28 |
| p99 | 674.68 |
| max | 3237.4 |

| threshold | rows exceeding | % of evaluated |
| :--- | ---: | ---: |
| > 25 km | 21486 | 15.22% |
| > 50 km | 12504 | 8.86% |
| > 75 km | 8869 | 6.28% |
| > 100 km | 6862 | 4.86% |
| > 150 km | 4826 | 3.42% |
| > 200 km | 4008 | 2.84% |

> Interpretation: the median office sits ~5.67 km from its pincode siblings and p75 is ~13.21 km, so there is a clear knee well below 50 km. Points beyond ~100 km (6862 rows) are almost certainly bad coordinates; the 50–100 km band is ambiguous (some genuinely large rural pincodes). Suspects are flagged, not deleted: findNearby excludes them by default but `includeSuspect` recovers them, and pincode centroids ignore them.

Sampled flagged-distance range: 50.67–2169.34 km (median 87.3 km).

20 random flagged rows (deterministic sample):

| pincode | office | state | district | lat | lon | rule | dist_km |
| :--- | :--- | :--- | :--- | ---: | ---: | :--- | ---: |
| 387335 | Sastapur BO | GUJARAT | KHEDA | 15.5934 | 76.9183 | sibling | 489.61 |
| 272127 | Hiyaroopur BO | UTTAR PRADESH | BASTI | 27.126345 | 82.235647 | sibling | 72.43 |
| 494337 | Navagaon BO | CHHATTISGARH | RAIPUR | 20.1541 | 81.0214 | sibling | 50.67 |
| 210125 | Kharauli BO | UTTAR PRADESH | BANDA | 26.168626 | 80.513257 | sibling | 81.12 |
| 229309 | Fatehpur BO | UTTAR PRADESH | AMETHI | 25.84 | 80.89 | sibling | 77.24 |
| 313604 | Dhamniya Jageer | RAJASTHAN | UDAIPUR | 24.204538 | 73.305954 | sibling | 95.61 |
| 464551 | Pathari B.O | MADHYA PRADESH | RAISEN | 19.26324 | 76.430277 | sibling | 476.33 |
| 604203 | Melolakkur SO | TAMIL NADU | VILLUPURAM | 11.377111 | 79.491583 | sibling | 121.22 |
| 721603 | Natshal BO | WEST BENGAL | MEDINIPUR EAST | 15.5934 | 88.0368 | sibling | 727.92 |
| 229303 | Kundanganj BO | UTTAR PRADESH | RAE BARELI | 26.45 | 81.11 | sibling | 207.34 |
| 441209 | Chilamtola B.O | MAHARASHTRA | GADCHIROLI | 20.054992 | 79.989203 | sibling | 71.28 |
| 273413 | Karjhi BO | UTTAR PRADESH | GORAKHPUR | 27.275508 | 83.329962 | sibling | 83.14 |
| 144105 | Kathe Adhkare BO | PUNJAB | HOSHIARPUR | 31.81 | 75.56 | sibling | 63.14 |
| 793119 | Mawmluh II | MEGHALAYA | WEST JAINTIA HILLS | 25.257946 | 91.707176 | sibling | 60.01 |
| 800011 | Makhdumpur Digha SO | BIHAR | PATNA | 24.212246 | 90.962952 | district | 595.74 |
| 222149 | Kusarana BO | UTTAR PRADESH | JAUNPUR | 26.58 | 82.99 | sibling | 76.67 |
| 577599 | Beeranahally B.O | KARNATAKA | CHITRADURGA | 13.95421 | 75.672936 | sibling | 91.45 |
| 815315 | Lataki BO | JHARKHAND | GIRIDIH | 24.23 | 86.12 | sibling | 58.82 |
| 148031 | Haryau BO | PUNJAB | SANGRUR | 12.5456 | 85.323213 | sibling | 2169.34 |
| 481998 | Ahmadpur B.O | MADHYA PRADESH | MANDLA | 18.706194 | 76.938379 | sibling | 749.95 |

## Multi-district / cross-state pincodes (report only, not modified)

Pincodes mapped to more than one district: 1478.
Pincodes whose districts span more than one STATE (possible source errors): 52.

Sample cross-state pincodes:

| pincode | states |
| :--- | :--- |
| 110025 | ['DELHI', 'UTTAR PRADESH'] |
| 244923 | ['UTTAR PRADESH', 'UTTARAKHAND'] |
| 244924 | ['UTTAR PRADESH', 'UTTARAKHAND'] |
| 247662 | ['UTTAR PRADESH', 'UTTARAKHAND'] |
| 305402 | ['RAJASTHAN', 'TELANGANA'] |
| 311601 | ['RAJASTHAN', 'TELANGANA'] |
| 332028 | ['RAJASTHAN', 'TELANGANA'] |
| 333022 | ['RAJASTHAN', 'TELANGANA'] |
| 335513 | ['RAJASTHAN', 'TELANGANA'] |
| 335526 | ['RAJASTHAN', 'TELANGANA'] |
| 343027 | ['RAJASTHAN', 'TELANGANA'] |
| 396193 | ['GUJARAT', 'THE DADRA AND NAGAR HAVELI AND DAMAN AND DIU'] |
| 396215 | ['GUJARAT', 'THE DADRA AND NAGAR HAVELI AND DAMAN AND DIU'] |
| 396230 | ['GUJARAT', 'THE DADRA AND NAGAR HAVELI AND DAMAN AND DIU'] |
| 396235 | ['GUJARAT', 'THE DADRA AND NAGAR HAVELI AND DAMAN AND DIU'] |
| 396240 | ['GUJARAT', 'THE DADRA AND NAGAR HAVELI AND DAMAN AND DIU'] |
| 503145 | ['ANDHRA PRADESH', 'TELANGANA'] |
| 503188 | ['ANDHRA PRADESH', 'TELANGANA'] |
| 503225 | ['ANDHRA PRADESH', 'TELANGANA'] |
| 503230 | ['ANDHRA PRADESH', 'TELANGANA'] |

Rows whose state disagrees with the pincode's 2-digit postal prefix: 6590.

Sample prefix mismatches:

| pincode | state | expected_region_states |
| :--- | :--- | :--- |
| 503321 | ANDHRA PRADESH | ['TELANGANA'] |
| 503230 | ANDHRA PRADESH | ['TELANGANA'] |
| 781131 | MEGHALAYA | ['ASSAM'] |
| 504346 | ANDHRA PRADESH | ['TELANGANA'] |
| 504346 | ANDHRA PRADESH | ['TELANGANA'] |
| 504346 | ANDHRA PRADESH | ['TELANGANA'] |
| 504346 | ANDHRA PRADESH | ['TELANGANA'] |
| 504346 | ANDHRA PRADESH | ['TELANGANA'] |
| 504346 | ANDHRA PRADESH | ['TELANGANA'] |
| 825320 | JHARKHAND | ['BIHAR'] |
| 815317 | JHARKHAND | ['BIHAR'] |
| 815317 | JHARKHAND | ['BIHAR'] |
| 815317 | JHARKHAND | ['BIHAR'] |
| 815317 | JHARKHAND | ['BIHAR'] |
| 825405 | JHARKHAND | ['BIHAR'] |
| 825311 | JHARKHAND | ['BIHAR'] |
| 825311 | JHARKHAND | ['BIHAR'] |
| 825311 | JHARKHAND | ['BIHAR'] |
| 825311 | JHARKHAND | ['BIHAR'] |
| 825311 | JHARKHAND | ['BIHAR'] |

## v1.0.4 reproduction diff

Comparison of this build (run against the committed `data/raw-data.csv`) versus the v1.0.4 baseline counts recorded in the Phase 0 audit.

| Metric | v1.0.4 | this build | delta |
| :--- | ---: | ---: | ---: |
| Unique pincodes | 19586 | 19586 | 0 |
| Post office rows | 165627 | 165625 | -2 |

Pincodes added vs v1.0.4 set: 0; removed: 0.

## Fresh-fetch diff

_No fresh fetch was performed (DATA_GOV_IN_API_KEY not set or --fetch not passed). Run `python -m pipeline.build --fetch` with the key to populate this._

## Sanity gates

| Gate | Result | Detail |
| :--- | :--- | :--- |
| pincode_count_within_pct | PASS | current=19586 previous=19586 diff=0.0000 limit=0.03 |
| post_office_count_within_pct | PASS | current=165625 previous=165627 diff=0.0000 limit=0.05 |
| all_states_have_pincodes | PASS | all canonical states present |
| null_coord_pct_under_limit | PASS | null_coord=13836 pct=0.0835 limit=0.2 |

## Attribution

> Department of Posts, Ministry of Communications, Government of India, 2020, All India Pincode Directory till last month, Open Government Data (OGD) Platform India, 26/11/2025, https://www.data.gov.in/resource/all-india-pincode-directory-till-last-month. Released under NDSAP and licensed under Government Open Data License - India: https://www.data.gov.in/Godl

