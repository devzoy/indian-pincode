"""Unit tests for the regex-gated source-date parser.

Uses the real API response saved (key-stripped) in pipeline/fixtures/api_sample.json
to assert we parse the actual field/format the data.gov.in API returns.
"""

import json
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

from pipeline import fetch  # noqa: E402

FIXTURE = os.path.join(REPO_ROOT, "pipeline", "fixtures", "api_sample.json")


def _load_fixture():
    with open(FIXTURE, encoding="utf-8") as f:
        return json.load(f)


def test_fixture_exists_and_has_updated_date():
    d = _load_fixture()
    assert "updated_date" in d, "API sample must contain updated_date"
    assert d["updated_date"], "updated_date must be non-empty"


def test_parses_real_api_updated_date():
    d = _load_fixture()
    # The real API returns ISO-8601 with a Zulu suffix, e.g. 2025-10-03T04:04:14Z.
    assert fetch.parse_source_updated_date(d["updated_date"]) == "2025-10-03"


def test_parses_real_api_created_date():
    d = _load_fixture()
    # created_date is an ISO date only.
    assert fetch.parse_source_updated_date(d["created_date"]) == "2020-12-20"


def test_parses_epoch_seconds_field():
    d = _load_fixture()
    # `updated` is epoch seconds; must resolve to the same calendar date.
    assert fetch.parse_source_updated_date(str(d["updated"])) == "2025-10-03"


@pytest.mark.parametrize("value,expected", [
    ("2025-10-03T04:04:14Z", "2025-10-03"),
    ("2025-10-03T04:04:14+05:30", "2025-10-02"),  # 04:04 IST -> prev day UTC
    ("2025-10-03", "2025-10-03"),
    ("03/10/2025", "2025-10-03"),                 # DD/MM/YYYY
    ("1759464254", "2025-10-03"),                 # epoch seconds
    ("1759464254000", "2025-10-03"),              # epoch millis
])
def test_known_formats(value, expected):
    assert fetch.parse_source_updated_date(value) == expected


@pytest.mark.parametrize("bad", [
    None, "", "   ", "NA", "n/a",
    "2025-13-03",          # impossible month (matches regex, fails strptime)
    "10/03/2025Z",         # junk suffix
    "Oct 3 2025",          # month name, unsupported
    "2025/10/03",          # slashes with year-first, unsupported
    "20251003",            # 8-digit, ambiguous, not a supported format
])
def test_rejects_unknown_or_ambiguous(bad):
    with pytest.raises(ValueError):
        fetch.parse_source_updated_date(bad)


def test_never_guesses_dd_mm_vs_mm_dd():
    # 03/10/2025 must be 3 Oct (DD/MM), never 10 Mar. The parser only accepts
    # DD/MM/YYYY, so an ambiguous value resolves deterministically.
    assert fetch.parse_source_updated_date("03/10/2025") == "2025-10-03"
