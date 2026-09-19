"""Fetch step for the build pipeline.

Two modes:
  * API mode: download all pages from the data.gov.in resource using the API key
    from the DATA_GOV_IN_API_KEY environment variable. Verifies the fetched row
    count against the API-reported `total`, retries with exponential backoff on
    transient errors, and NEVER logs the API key.
  * Local mode: read an existing CSV file (default: data/raw-data.csv).

Both modes return a FetchResult with the rows, the raw bytes, a SHA-256 of the raw
bytes, an ISO-8601 fetch timestamp, and the parsed source_updated_date (from the
API's `updated_date` field). In local mode, source_updated_date is None and the
caller (build) must obtain it another way or fail per policy.

This is the ONLY module permitted to make network calls, and only when do_fetch
is requested.
"""

from __future__ import annotations

import csv
import datetime as _dt
import hashlib
import io
import json
import os
import re
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from . import config


@dataclass
class FetchResult:
    rows: List[Dict[str, str]]
    raw_bytes: bytes
    sha256: str
    fetched_at: str  # ISO-8601 UTC
    source_updated_date: Optional[str]  # ISO-8601 date (YYYY-MM-DD) or None
    source: str  # "api" or "local"
    raw_path: Optional[str] = None


# ---- secret redaction ------------------------------------------------------
# The API key must never appear in any log line, exception message, or traceback.
# We register the active key(s) and scrub them from any string we emit or raise.
_REDACT_SECRETS: set = set()


def _register_secret(secret: str) -> None:
    if secret:
        _REDACT_SECRETS.add(secret)


def _redact(text) -> str:
    """Replace any registered secret in `text` with '***'. Also scrubs an
    api-key=... query param value defensively, even if the exact key wasn't
    registered."""
    s = str(text)
    for secret in _REDACT_SECRETS:
        if secret:
            s = s.replace(secret, "***")
    # Defensive: scrub api-key query values regardless of registration.
    s = re.sub(r"(api-key=)[^&\s'\"]+", r"\1***", s)
    return s


class FetchError(RuntimeError):
    """A fetch failure whose message is guaranteed to be redacted."""

    def __init__(self, message: str):
        super().__init__(_redact(message))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


# Explicit, regex-gated date formats. Each entry is (compiled regex, strptime
# format or the sentinel "EPOCH"). A value is parsed ONLY if a regex matches
# exactly; we never fall through to a generic/fuzzy parser and never guess
# between DD/MM and MM/DD. The formats supported are exactly those observed on
# the data.gov.in API (see pipeline/fixtures/api_sample.json):
#   updated_date : "2025-10-03T04:04:14Z"  (ISO-8601 with Zulu)
#   created_date : "2020-12-20"            (ISO-8601 date only)
#   updated      : 1759464254              (epoch seconds)
# The DD/MM/YYYY form is included because the data.gov.in HTML surfaces render
# dates that way; it is only ever used when the value unambiguously matches
# that pattern.
_DATE_FORMATS = [
    (re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"), "ISO_ZULU"),
    (re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$"), "%Y-%m-%dT%H:%M:%S%z"),
    (re.compile(r"^\d{4}-\d{2}-\d{2}$"), "%Y-%m-%d"),
    (re.compile(r"^\d{2}/\d{2}/\d{4}$"), "%d/%m/%Y"),
    (re.compile(r"^\d{10}$"), "EPOCH_S"),
    (re.compile(r"^\d{13}$"), "EPOCH_MS"),
]


def parse_source_updated_date(raw_value) -> str:
    """Parse a data.gov.in date value into an ISO-8601 date string (YYYY-MM-DD).

    Strictly regex-gated: a value is parsed only when it matches one of the
    KNOWN formats exactly. Never uses a generic parser, never guesses DD/MM vs
    MM/DD, and never falls back to the fetch time. Raises ValueError otherwise.
    """
    if raw_value is None:
        raise ValueError("source date is missing (None)")
    value = str(raw_value).strip()
    if not value:
        raise ValueError("source date is empty")

    for pattern, fmt in _DATE_FORMATS:
        if not pattern.match(value):
            continue
        if fmt == "ISO_ZULU":
            dt = _dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=_dt.timezone.utc
            )
            return dt.date().isoformat()
        if fmt == "EPOCH_S":
            return _dt.datetime.fromtimestamp(int(value), _dt.timezone.utc).date().isoformat()
        if fmt == "EPOCH_MS":
            return _dt.datetime.fromtimestamp(int(value) // 1000, _dt.timezone.utc).date().isoformat()
        if fmt == "%Y-%m-%dT%H:%M:%S%z":
            # Normalize any timezone offset to UTC before taking the calendar date,
            # so tz-aware values are deterministic and consistent with the Zulu form.
            dt = _dt.datetime.strptime(value, fmt).astimezone(_dt.timezone.utc)
            return dt.date().isoformat()
        return _dt.datetime.strptime(value, fmt).date().isoformat()

    raise ValueError(f"source date {value!r} does not match any known format")


def _iter_csv(text: str) -> List[Dict[str, str]]:
    reader = csv.DictReader(io.StringIO(text))
    return [dict(row) for row in reader]


def from_local(path: str) -> FetchResult:
    """Read an existing local CSV (plain or .gz). No network access.

    For a .gz file, the sha256 is computed over the DECOMPRESSED CSV bytes so it
    matches an equivalent plain-CSV or fresh-API export."""
    if path.endswith(".gz"):
        import gzip
        with gzip.open(path, "rb") as f:
            raw = f.read()
    else:
        with open(path, "rb") as f:
            raw = f.read()
    text = raw.decode("utf-8")
    rows = _iter_csv(text)
    return FetchResult(
        rows=rows,
        raw_bytes=raw,
        sha256=_sha256(raw),
        fetched_at=_now_iso(),
        source_updated_date=None,
        source="local",
        raw_path=path,
    )


def from_api(
    api_key: str,
    resource_id: str = config.RESOURCE_ID,
    page_size: int = 1000,
    max_retries: int = 5,
    save_dir: str = config.RAW_DIR,
) -> FetchResult:
    """Fetch all pages from the data.gov.in resource.

    Uses only the standard library (urllib) to avoid adding a runtime dependency.
    Never logs the API key.
    """
    import urllib.parse

    _register_secret(api_key)
    base = f"{config.API_BASE}/{resource_id}"
    all_records: List[Dict[str, str]] = []
    total: Optional[int] = None
    source_updated_raw: Optional[str] = None
    offset = 0

    while True:
        params = {
            "api-key": api_key,
            "format": "json",
            "offset": str(offset),
            "limit": str(page_size),
        }
        url = f"{base}?{urllib.parse.urlencode(params)}"

        payload = _get_with_backoff(url, max_retries)
        # Never log `url` (contains the key). Log only offset/limit.
        if total is None:
            total = int(payload.get("total", 0) or 0)
            source_updated_raw = payload.get("updated_date")
        records = payload.get("records", []) or []
        if not records:
            break
        all_records.extend(records)
        print(f"[fetch] pulled {len(all_records)}/{total} rows (offset={offset})")
        offset += page_size
        if total and len(all_records) >= total:
            break

    if total is not None and len(all_records) != total:
        raise FetchError(
            f"fetched row count {len(all_records)} != API total {total}"
        )

    # Serialize records to CSV in the canonical column order for hashing/storage.
    raw_bytes = _records_to_csv_bytes(all_records)
    sha = _sha256(raw_bytes)

    # Persist raw file + sidecar metadata (gitignored dir).
    os.makedirs(save_dir, exist_ok=True)
    raw_path = os.path.join(save_dir, "raw-data.csv")
    with open(raw_path, "wb") as f:
        f.write(raw_bytes)
    fetched_at = _now_iso()
    with open(raw_path + ".meta.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "sha256": sha,
                "fetched_at": fetched_at,
                "row_count": len(all_records),
                "api_total": total,
                "source_updated_date_raw": source_updated_raw,
            },
            f,
            indent=2,
        )

    source_updated_iso = None
    if source_updated_raw is not None:
        print(f"[fetch] raw updated_date from API: {source_updated_raw!r}")
        source_updated_iso = parse_source_updated_date(source_updated_raw)

    return FetchResult(
        rows=_iter_csv(raw_bytes.decode("utf-8")),
        raw_bytes=raw_bytes,
        sha256=sha,
        fetched_at=fetched_at,
        source_updated_date=source_updated_iso,
        source="api",
        raw_path=raw_path,
    )


def _get_with_backoff(url: str, max_retries: int) -> dict:
    """GET a JSON page with retry + exponential backoff (urllib only).

    We never shell out (see _http_get): the API key is in the URL and a
    subprocess would expose it in process arguments. Errors are redacted before
    they are logged or raised, so the key never appears in output.
    """
    delay = 1.0
    last_err_type = None
    last_err_msg = None
    for attempt in range(1, max_retries + 1):
        try:
            data = _http_get(url)
            return json.loads(data.decode("utf-8"))
        except Exception as e:  # noqa: BLE001 - transient network/parse errors
            last_err_type = type(e).__name__
            # str(e) from urllib may embed the full URL (with the key); redact it.
            last_err_msg = _redact(str(e))
            print(f"[fetch] attempt {attempt}/{max_retries} failed: {last_err_type}; "
                  f"retrying in {delay:.1f}s")
            time.sleep(delay)
            delay = min(delay * 2, 30.0)
    raise FetchError(
        f"fetch failed after {max_retries} retries: {last_err_type}: {last_err_msg}"
    )


_UA = "indian-pincode-pipeline/2.0 (+https://github.com/devzoy/indian-pincode)"


def _http_get(url: str) -> bytes:
    """GET a URL with urllib only.

    We deliberately do NOT shell out to curl: the API key is in the URL, and any
    subprocess would expose it in process arguments (visible via `ps` and in some
    CI logs). urllib keeps the key inside the process. A generous timeout avoids
    the slow-response hangs seen on the data.gov.in endpoint.
    """
    import urllib.request
    import urllib.error

    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": _UA})
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        # HTTPError.__str__ / .url can contain the key; raise a redacted error.
        raise FetchError(f"HTTP {e.code} from data.gov.in") from None
    except urllib.error.URLError as e:
        raise FetchError(f"URL error: {_redact(str(e.reason))}") from None


def _records_to_csv_bytes(records: List[Dict[str, str]]) -> bytes:
    # Sort records deterministically so the raw file (and its SHA-256) is stable
    # regardless of the order the API returns pages in. Sort by the full column
    # tuple to get a total order.
    def _key(rec):
        return tuple((rec.get(col) or "") for col in config.EXPECTED_COLUMNS)

    ordered = sorted(records, key=_key)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=config.EXPECTED_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for rec in ordered:
        writer.writerow({col: rec.get(col, "") for col in config.EXPECTED_COLUMNS})
    return buf.getvalue().encode("utf-8")


def fetch(cfg: config.Config) -> Optional[FetchResult]:
    """Entry point used by build.

    Returns a FetchResult if an API fetch happened, else None (build will fall
    back to the local CSV via from_local). If do_fetch is True but the API key is
    unset, prints a message and returns None WITHOUT failing (per policy).
    """
    if not cfg.do_fetch:
        return None
    api_key = os.environ.get(config.API_KEY_ENV)
    if not api_key:
        print(f"[fetch] {config.API_KEY_ENV} not set; skipping fetch (not an error).")
        return None
    _register_secret(api_key)
    print("[fetch] fetching from data.gov.in API (key present, not logged)...")
    return from_api(api_key, page_size=cfg.page_size)
