# Benchmarks

Measured on macOS (arm64), Python 3.13.1, Node v22.22.3. Latencies are warm
(after `preload()`), median (p50) and p99 over thousands of iterations. Your
numbers will differ by machine, but the relative before/after holds.

## Package size

| Package | v1.0.4 | v2.0.0 | Budget (target) |
| :--- | ---: | ---: | :--- |
| npm core `@devzoy/indian-pincode` (unpacked) | 41.1 MB | **470 KB** | ≤500 KB (≤300 KB) |
| npm geo `@devzoy/indian-pincode-geo` (unpacked) | — | **2.8 MB** | ≤10 MB (≤6 MB) |
| PyPI core `indian-pincode` (wheel) | 9.77 MB | **~29 KB** | — |
| PyPI core data (unpacked in wheel) | — | **~260 KB** | ≤500 KB (≤300 KB) |
| PyPI geo `indian-pincode-geo` (wheel) | — | **4.05 MB** | — |
| PyPI geo data (unpacked SQLite) | — | **9.8 MB** | ≤10 MB (≤6 MB) |

Notes:
- npm core is 470 KB unpacked because the data is inlined into **both** the CJS and
  ESM builds (~235 KB each) for zero-config browser/bundler support. This is under the
  500 KB budget but over the 300 KB stretch target. See ACTION NEEDED in the summary.
- PyPI geo SQLite is 9.8 MB unpacked (under the 10 MB budget, over the 6 MB target).

## Cold load (fresh process, import/require + first use)

| | v1.0.4 | v2.0.0 |
| :--- | ---: | ---: |
| Python core (import + first validate) | ~10 ms | ~23 ms* |
| Python geo (import + first lookup) | — | ~65–110 ms* |
| Node core (require + first validate) | ~0.5 ms (lazy) | ~4.5 ms |
| Node geo (require + first lookup) | — | ~64 ms |

\* Python "cold" includes interpreter import machinery; the data decode itself is
~9 ms (core) and the geo cold builds the in-memory pincode index over 165 k rows.
All are one-time and comfortably under interactive thresholds.

## Operation latency (warm, p50 / p99 in ms)

### Core

| function | Python p50 | Python p99 | Node p50 | Node p99 |
| :--- | ---: | ---: | ---: | ---: |
| validate | 0.0005 | 0.0007 | 0.0001 | 0.0005 |
| getDetails / get_details | 0.0010 | 0.0014 | 0.0002 | 0.0006 |
| getState / get_state | 0.0010 | 0.0015 | 0.0001 | 0.0002 |
| getPincodes / get_pincodes (state) | 0.655 | 0.785 | 0.022 | 0.055 |
| getCentroid / get_centroid (geo) | 0.0062 | 0.0097 | 0.0000 | 0.0002 |

### Geo

| function | Python p50 | Python p99 | Node p50 | Node p99 |
| :--- | ---: | ---: | ---: | ---: |
| lookup | 0.027 | 0.054 | 0.0007 | 0.0064 |
| findNearby / find_nearby (5 km) | 0.581 | 1.192 | 0.020 | 0.097 |
| reverseLookup / reverse_lookup | 0.653 | 0.755 | 0.007 | 0.031 |

## Before/after for the v1 operations

| operation | v1 Python | v1 Node | v2 Python | v2 Node |
| :--- | ---: | ---: | ---: | ---: |
| validate (p50) | 0.0008 | 0.0002 | 0.0005 | 0.0001 |
| lookup (p50) | 0.074 (new SQLite conn/call) | 0.17 (async) | 0.027 | 0.0007 |
| findNearby 5 km (p50) | 9.9 | ~6 (full scan/call) | 0.581 | 0.020 |
| findNearby 5 km (p99) | 12.0 | ~8 | 1.192 | 0.097 |

`findNearby` is the headline win: the 0.1° grid index (Node) and grid-cell SQLite index
(Python) replaced full scans, cutting p99 from ~8–12 ms to ~0.1 ms (Node) / ~1.2 ms
(Python) — both far under the 5 ms p99 target.

## Correctness

`findNearby` was checked against a brute-force haversine scan over all points on 500
random query points in both languages: **identical results**.
