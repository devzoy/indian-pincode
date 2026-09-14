"""--from-csv manual import runs through the same schema gate, normalization, and
gates, and records provenance in build_log.json (not metadata.json)."""

import csv
import io
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

from pipeline import config, fetch, normalize  # noqa: E402

FIXTURE = os.path.join(REPO_ROOT, "tests", "fixtures", "mini-raw.csv")


def test_from_csv_reads_and_normalizes_fixture():
    fr = fetch.from_local(FIXTURE)
    assert fr.source == "local"
    rows, stats = normalize.normalize(fr.rows)
    # 4 input rows, all valid pincodes, no dupes
    assert stats["input_rows"] == 4
    assert stats["invalid_pincode_dropped"] == 0
    pincodes = {r["pincode"] for r in rows}
    assert pincodes == {"560095", "110001"}
    # office types preserved verbatim
    assert {r["office_type"] for r in rows} == {"PO", "BO", "HO"}


def test_from_csv_schema_gate_fails_on_missing_column():
    # Drop a required column ("latitude") -> schema gate must fail.
    with open(FIXTURE, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r.pop("latitude", None)
    with pytest.raises(RuntimeError, match="schema gate"):
        normalize.normalize(rows)


def test_from_csv_config_sets_manual_origin():
    cfg = config.Config(local_csv=FIXTURE, source_origin="manual_csv")
    assert cfg.source_origin == "manual_csv"
    assert cfg.do_fetch is False


def test_from_csv_coordinates_cleaned():
    # The Baroda House row has NA coords -> geo_quality "missing".
    fr = fetch.from_local(FIXTURE)
    rows, _ = normalize.normalize(fr.rows)
    from pipeline import coordinates
    cleaned, _ = coordinates.clean(rows, config.Thresholds())
    baroda = next(r for r in cleaned if r["office_name"] == "Baroda House S.O")
    assert baroda["latitude"] is None
    assert baroda["geo_quality"] == "missing"
