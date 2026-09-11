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


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def parse_source_updated_date(raw_value: str) -> str:
    """Parse the data.gov.in `updated_date` value into an ISO-8601 date string.

    data.gov.in renders dates as DD/MM/YYYY (optionally with a time component).
    We parse EXPLICITLY with that format and never fall back to a generic parser
    or to the fetch time. Raises ValueError if it cannot be parsed.
    """
    if raw_value is None:
        raise ValueError("source updated_date is missing")
    value = str(raw_value).strip()
    if not value:
        raise ValueError("source updated_date is empty")

    # The field may be an epoch (seconds) in some API responses, or DD/MM/YYYY,
    # or DD/MM/YYYY HH:MM:SS. Handle each explicitly.
    # 1) Pure integer -> treat as epoch seconds.
    if value.isdigit():
        ts = int(value)
        # data.gov.in sometimes uses ms epochs; detect by magnitude.
        if ts > 10_000_000_000:
            ts //= 1000
        return _dt.datetime.fromtimestamp(ts, _dt.timezone.utc).date().isoformat()

    # 2) DD/MM/YYYY with optional time.
    date_part = value.split(" ")[0]
    dt = _dt.datetime.strptime(date_part, "%d/%m/%Y")
    return dt.date().isoformat()


def _iter_csv(text: str) -> List[Dict[str, str]]:
    reader = csv.DictReader(io.StringIO(text))
    return [dict(row) for row in reader]


def from_local(path: str) -> FetchResult:
    """Read an existing local CSV. No network access."""
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
    import urllib.request
    import urllib.error

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
        raise RuntimeError(
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
    import urllib.request
    import urllib.error

    delay = 1.0
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
            return json.loads(data.decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            last_err = e
            # Do not include the URL (has the key) in the message.
            print(f"[fetch] attempt {attempt}/{max_retries} failed: {type(e).__name__}; "
                  f"retrying in {delay:.1f}s")
            time.sleep(delay)
            delay = min(delay * 2, 30.0)
    raise RuntimeError(f"fetch failed after {max_retries} retries: {type(last_err).__name__}")


def _records_to_csv_bytes(records: List[Dict[str, str]]) -> bytes:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=config.EXPECTED_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for rec in records:
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
    print("[fetch] fetching from data.gov.in API (key present, not logged)...")
    return from_api(api_key)
