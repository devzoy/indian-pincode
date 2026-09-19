"""Canonical data build pipeline for indian-pincode.

Single source of truth: transforms the India Post "All India Pincode Directory"
(data.gov.in resource) into a normalized, cleaned canonical dataset plus metadata
and a human-readable report. Per-language artifacts (Phase 3) are generated from
the canonical file.

Run with:  python -m pipeline.build [options]

The pipeline performs NO network access except the explicit fetch step
(pipeline.fetch), which is only used when --fetch is passed and DATA_GOV_IN_API_KEY
is set. All other steps operate on local files.
"""

__all__ = ["config", "fetch", "normalize", "coordinates", "gates", "outputs", "build"]
