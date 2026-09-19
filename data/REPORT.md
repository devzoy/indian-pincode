# Data Build Report

- **data_version:** `2025.10.03`
- **source_updated_date:** `2025-10-03` (as reported by the API)
- **content_sha256:** `d50375aaa0fc2d41e2a798abcba93df5eee71eb84418596516f017d3d69e84f9` (hash of the normalized data; drives refresh PRs)
- **source SHA-256:** `53a708b501d1ffeb56e2b2a3d165535edb3db0a1669f4eb96467121629603385`

_Note: this report is derived only from the source data and is byte-stable across re-runs on the same source. Run-time details (fetch time, duration) are written to the gitignored `pipeline/raw/build_log.json`._

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

Circle-inferred rows, by the (strictly single-state) circle used:

| circle | canonical state | rows |
| :--- | :--- | ---: |
| Chattisgarh Circle | (single-state) | 2 |
| Haryana Circle | (single-state) | 5 |
| Karnataka Circle | (single-state) | 1 |
| Madhya Pradesh Circle | (single-state) | 9 |
| Uttarakhand Circle | (single-state) | 1 |

District rename/variant mappings applied (only entries whose source spelling actually appears in the data):
 none.

## Coordinate cleaning

| Rule | Count |
| :--- | ---: |
| Both missing/NA/non-numeric -> null (missing) | 12006 |
| Partial (one of lat/lon null) -> null (missing) | 9 |
| In-box original | 150998 |
| Swapped (lon,lat) -> valid | 791 |
| Removed (out of box, swap did not help / garbage) | 1821 |
| Suspect via sibling-median rule | 10595 |
| Suspect via district-median fallback | 91 |

geo_quality distribution:

| geo_quality | rows |
| :--- | ---: |
| original | 140397 |
| swapped | 706 |
| suspect | 10686 |
| removed | 1821 |
| missing | 12015 |

## Outlier sanity check

Total suspect rows: 10686 (sibling rule: 10595, district fallback: 91).

**Adaptive outlier rule (sibling branch):** max(40.0km, 5.0x spread), hard cap 150.0km. n=141136 offices evaluated against their same-pincode siblings.

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
| > 40 km | 14990 | 10.62% |
| > 50 km | 12504 | 8.86% |
| > 75 km | 8869 | 6.28% |
| > 100 km | 6862 | 4.86% |
| > 150 km | 4826 | 3.42% |
| > 200 km | 4008 | 2.84% |

**New adaptive rule vs legacy fixed-50 km rule (sibling branch):**

| rule | flagged (sibling) | % of all rows |
| :--- | ---: | ---: |
| legacy: > 50 km | 12504 | 7.55% |
| new: max(40 km, 5x spread), hard 150 km | 10595 | 6.40% |

Rows flagged ONLY by the new rule: 1166. Rows suspect under 50 km but NO LONGER flagged: 3075.

**10 rows flagged ONLY by the new adaptive rule:**

| pincode | office | state | district | lat | lon | rule | dist_km |
| :--- | :--- | :--- | :--- | ---: | ---: | :--- | ---: |
| 711315 | Khurigachi BO | WEST BENGAL | HOWRAH | 22.8336 | 88.0219 | sibling | 47.61 |
| 587207 | Katagur B.O | KARNATAKA | BAGALKOT | 16.061178 | 76.05465 | sibling | 40.69 |
| 733125 | Bartakigram BO | WEST BENGAL | DINAJPUR DAKSHIN | 25.36 | 88.73 | sibling | 46.27 |
| 636808 | Hanumanthapuram B.O | TAMIL NADU | DHARMAPURI | 12.12 | 78.480322 | sibling | 49.09 |
| 572115 | Bukkapatna S.O | KARNATAKA | TUMAKURU | 13.3168611 | 77.1086389 | sibling | 46.98 |
| 283114 | Naugawan BO | UTTAR PRADESH | AGRA | 27.01047 | 78.3756899 | sibling | 41.46 |
| 401201 | Mulgaon B.O | MAHARASHTRA | PALGHAR | 19.4238585 | 72.398529 | sibling | 42.28 |
| 534235 | Apparaopeta B.O | ANDHRA PRADESH | WEST GODAVARI | 16.89825 | 81.570268 | sibling | 40.7 |
| 175017 | Batwara BO | HIMACHAL PRADESH | MANDI | 31.6 | 77.28 | sibling | 44.8 |
| 635103 | Bagalur S.O (Krishnagiri) | TAMIL NADU | KRISHNAGIRI | 12.5275 | 78.2161944 | sibling | 47.72 |

**10 rows that were suspect at 50 km but are no longer flagged:**

| pincode | office | state | district | lat | lon | rule | dist_km |
| :--- | :--- | :--- | :--- | ---: | ---: | :--- | ---: |
| 403506 | Cotorem B.O | GOA | NORTH GOA | 16.23 | 74.38 | None | 118.72 |
| 472442 | Niwari S.O | MADHYA PRADESH | NIWARI | 25.3521 | 78.8015 | None | 91.77 |
| 382250 | Unchadi BO | GUJARAT | AHMADABAD | 23.16 | 72.03 | None | 65.97 |
| 834009 | Ranchi Medical College Campus SO | JHARKHAND | RANCHI | 23.3907222 | 85.3485 | None | 67.98 |
| 484770 | Maharoai | MADHYA PRADESH | SHAHDOL | 23.6586327 | 80.9137336 | None | 52.99 |
| 494334 | Mandri BO | CHHATTISGARH | RAIPUR | 20.153 | 81.0156 | None | 50.49 |
| 494665 | Hindu Binapal BO | CHHATTISGARH | KANKER | 20.1444 | 80.15648 | None | 83.19 |
| 412207 | Telewadi B.O | MAHARASHTRA | PUNE | 18.4630636 | 74.5788809 | None | 52.9 |
| 494220 | Khachgaon BO | CHHATTISGARH | KONDAGAON | 20.125 | 81.1855 | None | 78.54 |
| 441207 | Koregaon B.O | MAHARASHTRA | GADCHIROLI | 19.696635 | 79.160718 | None | 117.28 |

> Suspects are flagged, not deleted: findNearby excludes them by default but `includeSuspect` recovers them, and pincode centroids ignore them.

**20 random rows flagged as suspect (either rule):**

| pincode | office | state | district | lat | lon | rule | dist_km |
| :--- | :--- | :--- | :--- | ---: | ---: | :--- | ---: |
| 712123 | Somra BO | WEST BENGAL | HOOGHLY | 22.82 | 87.88 | sibling | 60.05 |
| 385320 | Sanesada B.O | GUJARAT | BANAS KANTHA | 24.169763 | 72.424496 | sibling | 86.86 |
| 535183 | Cheedivalasa B.O | ANDHRA PRADESH | VIZIANAGARAM | 18.4990205 | 83.8256166 | sibling | 94.39 |
| 451225 | Kodlya Khedi B.O | MADHYA PRADESH | KHARGONE | 24.87 | 76.0014 | sibling | 297.8 |
| 686611 | Memuri BO | KERALA | KOTTAYAM | 15.5934 | 76.5351 | sibling | 641.93 |
| 574228 | Mundaje S.O | KARNATAKA | DAKSHINA KANNADA | 12.46 | 75.13 | sibling | 69.95 |
| 388150 | Ramodadi B.O | GUJARAT | ANAND | 22.272543 | 72.411685 | sibling | 47.95 |
| 493663 | Kurud SO | CHHATTISGARH | DHAMTARI | 20.8320833 | 81.7160556 | sibling | 91.54 |
| 274702 | Bhatpar Rani SO | UTTAR PRADESH | DEORIA | 26.21 | 83.26 | sibling | 64.68 |
| 494001 | Bademurma B.O | CHHATTISGARH | RAIPUR | 18.58 | 82.04 | sibling | 54.94 |
| 212104 | Sonversa BO | UTTAR PRADESH | PRAYAGRAJ | 26.974724 | 82.471891 | sibling | 182.15 |
| 144209 | Chowki Patiari BO | PUNJAB | HOSHIARPUR | 30.23 | 74.12 | sibling | 155.3 |
| 788819 | Nabdi Daolangupu BO | ASSAM | DIMA HASAO | 25.256807 | 92.999926 | sibling | 75.96 |
| 785663 | Afala B.O | ASSAM | SIVASAGAR | 24.1518 | 92.5816 | sibling | 111.19 |
| 490001 | Bhilai 1 SO | CHHATTISGARH | DURG | 21.717302 | 81.53408 | sibling | 73.61 |
| 577529 | Kondlahalli S.O | KARNATAKA | CHITRADURGA | 14.2215833 | 76.3974167 | sibling | 57.32 |
| 678582 | Paloor BO | KERALA | PALAKKAD | 15.5934 | 75.5598 | sibling | 217.78 |
| 504101 | Boregaon B.O | TELANGANA | NIRMAL | 17.0477624 | 80.0981868 | sibling | 304.78 |
| 246443 | Bharki BO | UTTARAKHAND | CHAMOLI | 30.306407 | 78.998195 | sibling | 61.8 |
| 535273 | Melia Kancheru B.O | ANDHRA PRADESH | PARVATHIPURAM MANYAM | 17.970035 | 83.543996 | sibling | 51.62 |

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

Rows whose state is OUTSIDE the allowed set for its pincode prefix: 46 (0.03% of rows).

Mismatch counts by 3-digit prefix (top 15):

| prefix | count |
| :--- | ---: |
| 160 | 12 |
| 362 | 5 |
| 799 | 5 |
| 781 | 4 |
| 673 | 4 |
| 343 | 2 |
| 335 | 2 |
| 533 | 1 |
| 782 | 1 |
| 802 | 1 |
| 110 | 1 |
| 384 | 1 |
| 756 | 1 |
| 305 | 1 |
| 311 | 1 |

20 sample prefix mismatches:

| pincode | state | allowed_states |
| :--- | :--- | :--- |
| 533464 | PUDUCHERRY | ['ANDHRA PRADESH', 'TELANGANA'] |
| 782410 | MEGHALAYA | ['ASSAM'] |
| 781131 | MEGHALAYA | ['ASSAM'] |
| 781131 | MEGHALAYA | ['ASSAM'] |
| 781029 | MEGHALAYA | ['ASSAM'] |
| 781131 | MEGHALAYA | ['ASSAM'] |
| 802131 | UTTAR PRADESH | ['BIHAR', 'JHARKHAND'] |
| 110025 | UTTAR PRADESH | ['DELHI'] |
| 384316 | RAJASTHAN | ['GUJARAT'] |
| 362570 | THE DADRA AND NAGAR HAVELI AND DAMAN AND DIU | ['GUJARAT'] |
| 362520 | THE DADRA AND NAGAR HAVELI AND DAMAN AND DIU | ['GUJARAT'] |
| 362520 | THE DADRA AND NAGAR HAVELI AND DAMAN AND DIU | ['GUJARAT'] |
| 362540 | THE DADRA AND NAGAR HAVELI AND DAMAN AND DIU | ['GUJARAT'] |
| 362570 | THE DADRA AND NAGAR HAVELI AND DAMAN AND DIU | ['GUJARAT'] |
| 673310 | PUDUCHERRY | ['KERALA'] |
| 673310 | PUDUCHERRY | ['KERALA'] |
| 673310 | PUDUCHERRY | ['KERALA'] |
| 673310 | PUDUCHERRY | ['KERALA'] |
| 799001 | TELANGANA | ['ARUNACHAL PRADESH', 'ASSAM', 'MANIPUR', 'MEGHALAYA', 'MIZORAM', 'NAGALAND', 'TRIPURA'] |
| 799001 | TELANGANA | ['ARUNACHAL PRADESH', 'ASSAM', 'MANIPUR', 'MEGHALAYA', 'MIZORAM', 'NAGALAND', 'TRIPURA'] |

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
| post_office_count_within_pct | PASS | current=165625 previous=165625 diff=0.0000 limit=0.05 |
| all_states_have_pincodes | PASS | all canonical states present |
| null_coord_pct_under_limit | PASS | null_coord=13836 pct=0.0835 limit=0.2 |

## Attribution

> Department of Posts, Ministry of Communications, Government of India, 2020, All India Pincode Directory till last month, Open Government Data (OGD) Platform India, 03/10/2025, https://www.data.gov.in/resource/all-india-pincode-directory-till-last-month. Released under NDSAP and licensed under Government Open Data License - India: https://www.data.gov.in/Godl

