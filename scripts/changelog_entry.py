#!/usr/bin/env python3
"""Prepend a CHANGELOG.md entry for a data refresh.

Usage:
  python scripts/changelog_entry.py --version 2.0.1 --old-data 2025.10.03 --new-data 2025.11.03

Summarizes the data diff from data/build/metadata.json (counts) so a human can see
what changed at a glance in the refresh PR.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHANGELOG = os.path.join(ROOT, "CHANGELOG.md")
META = os.path.join(ROOT, "data", "build", "metadata.json")


def _counts():
    with open(META, encoding="utf-8") as f:
        m = json.load(f)
    c = m["counts"]
    return c["pincode_count"], c["post_office_count"], m["content_sha256"]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--version", required=True)
    p.add_argument("--old-data", required=True)
    p.add_argument("--new-data", required=True)
    args = p.parse_args()

    pins, offices, sha = _counts()
    today = _dt.date.today().isoformat()
    entry = (
        f"## {args.version} - {today}\n\n"
        f"### Data refresh\n\n"
        f"- Data snapshot `{args.old_data}` -> `{args.new_data}`.\n"
        f"- {pins} pincodes, {offices} post offices.\n"
        f"- content_sha256 `{sha}`.\n\n"
    )

    existing = ""
    if os.path.exists(CHANGELOG):
        with open(CHANGELOG, encoding="utf-8") as f:
            existing = f.read()

    # Insert after the top-level "# Changelog" header if present, else prepend.
    if existing.startswith("# "):
        head, _, rest = existing.partition("\n")
        new = f"{head}\n\n{entry}{rest.lstrip()}"
    else:
        new = f"# Changelog\n\n{entry}{existing}"

    with open(CHANGELOG, "w", encoding="utf-8") as f:
        f.write(new)
    print(f"prepended CHANGELOG entry for {args.version}")


if __name__ == "__main__":
    main()
