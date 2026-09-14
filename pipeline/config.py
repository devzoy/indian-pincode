"""Configuration for the build pipeline. All thresholds are configurable here
and overridable via CLI flags in pipeline.build."""

from __future__ import annotations

import os
from dataclasses import dataclass, field, asdict
from typing import Dict, Any

# ---- Paths -----------------------------------------------------------------

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIPELINE_DIR = os.path.join(REPO_ROOT, "pipeline")
MAPPINGS_DIR = os.path.join(PIPELINE_DIR, "mappings")
RAW_DIR = os.path.join(PIPELINE_DIR, "raw")  # gitignored

DATA_DIR = os.path.join(REPO_ROOT, "data")
BUILD_DIR = os.path.join(DATA_DIR, "build")

DEFAULT_LOCAL_CSV = os.path.join(DATA_DIR, "raw-data.csv.gz")

NORMALIZED_PATH = os.path.join(BUILD_DIR, "pincodes.normalized.jsonl.gz")
CENTROIDS_PATH = os.path.join(BUILD_DIR, "centroids.json.gz")
METADATA_PATH = os.path.join(BUILD_DIR, "metadata.json")
REPORT_PATH = os.path.join(DATA_DIR, "REPORT.md")

# Previous-release baseline used for the sanity-gate diff and the report.
# When metadata.json from a prior build is unavailable, the pipeline falls back
# to these v1.0.4 baseline counts (recorded during the Phase 0 audit).
PREVIOUS_METADATA_PATH = METADATA_PATH  # a prior build's metadata, if present
V1_BASELINE = {
    "release": "1.0.4",
    "pincode_count": 19586,
    "post_office_count": 165627,
}

# ---- Data source -----------------------------------------------------------

# data.gov.in "All India Pincode Directory (till last month)" resource.
RESOURCE_ID = "5c2f62fe-5afa-4119-a499-fec9d604d5bd"
API_BASE = "https://api.data.gov.in/resource"
API_KEY_ENV = "DATA_GOV_IN_API_KEY"

# Expected source columns (schema gate).
EXPECTED_COLUMNS = [
    "circlename",
    "regionname",
    "divisionname",
    "officename",
    "pincode",
    "officetype",
    "delivery",
    "district",
    "statename",
    "latitude",
    "longitude",
]

# ---- Enums -----------------------------------------------------------------

# Office types kept verbatim from the source (HO=Head Office, PO=Sub Post Office,
# BO=Branch Office). No remapping.
OFFICE_TYPES = ["HO", "PO", "BO"]
# Deterministic sort order for lookup results.
OFFICE_TYPE_ORDER = {"HO": 0, "PO": 1, "BO": 2}

DELIVERY_STATUSES = ["Delivery", "Non Delivery"]

# geo_quality enum: original | swapped | removed | missing | suspect
GEO_QUALITY = ["original", "swapped", "removed", "missing", "suspect"]


@dataclass
class Thresholds:
    # Bounding box for valid India coordinates.
    lat_min: float = 6.5
    lat_max: float = 37.5
    lon_min: float = 68.0
    lon_max: float = 97.5

    # Outlier detection (adaptive sibling rule).
    sibling_min_count: int = 3            # min valid same-pincode siblings for primary rule
    sibling_floor_km: float = 40.0        # never flag below this distance
    sibling_spread_multiplier: float = 5.0  # flag if dist > max(floor, mult * spread)
    sibling_hard_km: float = 150.0        # always flag beyond this, regardless of spread
    # Legacy fixed threshold, kept only for the old-vs-new comparison in the report.
    sibling_legacy_flag_km: float = 50.0
    district_min_count: int = 5           # min valid district points to run fallback
    district_hard_km: float = 150.0       # fallback floor
    district_p95_multiplier: float = 2.0  # fallback = max(hard_km, mult * district p95)

    # Sanity gates (fractions).
    gate_pincode_pct: float = 0.03      # +/- 3%
    gate_post_office_pct: float = 0.05  # +/- 5%
    gate_max_null_coord_pct: float = 0.20  # <20% null coords


@dataclass
class Config:
    thresholds: Thresholds = field(default_factory=Thresholds)
    # Fetch/source options.
    local_csv: str = DEFAULT_LOCAL_CSV
    do_fetch: bool = False
    # If True, the sanity gates raise on violation; if False, they only warn
    # (used for the initial reproduction build where the baseline is the same file).
    enforce_gates: bool = True
    # ISO-8601 source_updated_date supplied for local builds (from --source-date).
    # The pipeline never derives this from the fetch time.
    local_source_date: str | None = None
    # API pagination page size.
    page_size: int = 5000
    # If set (a reason string), failing count gates within +/-10% become warnings
    # for this run; the reason is recorded in metadata.json and REPORT.md.
    accept_baseline_change: str | None = None
    # Provenance label for build_log.json: "api", "local", or "manual_csv".
    # Never written to metadata.json (which stays byte-stable regardless of origin).
    source_origin: str = "local"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "thresholds": asdict(self.thresholds),
            "local_csv": self.local_csv,
            "do_fetch": self.do_fetch,
            "enforce_gates": self.enforce_gates,
        }
