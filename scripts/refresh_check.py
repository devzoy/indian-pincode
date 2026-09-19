#!/usr/bin/env python3
"""Refresh helper: compare the freshly-built content_sha256 against the committed
one and emit machine-readable outputs for the data-refresh workflow.

Assumes a build has just run and written data/build/metadata.json. Compares its
content_sha256 to the version committed at HEAD.

Writes to $GITHUB_OUTPUT (if set):
  changed=true|false
  old_sha=<committed content_sha256 or "none">
  new_sha=<current content_sha256>
  old_version=<committed data_version or "none">
  new_version=<current data_version>

Exit code is always 0; the workflow branches on `changed`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
META_REL = "data/build/metadata.json"


def _current():
    with open(os.path.join(ROOT, META_REL), encoding="utf-8") as f:
        m = json.load(f)
    return m["content_sha256"], m["data_version"]


def _committed():
    try:
        blob = subprocess.run(
            ["git", "show", f"HEAD:{META_REL}"],
            cwd=ROOT, capture_output=True, text=True,
        )
        if blob.returncode != 0 or not blob.stdout:
            return None, None
        m = json.loads(blob.stdout)
        return m.get("content_sha256"), m.get("data_version")
    except Exception:  # noqa: BLE001
        return None, None


def main():
    new_sha, new_version = _current()
    old_sha, old_version = _committed()
    changed = old_sha != new_sha

    print(f"committed content_sha256: {old_sha}")
    print(f"fresh     content_sha256: {new_sha}")
    print(f"changed: {changed}")

    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"changed={'true' if changed else 'false'}\n")
            f.write(f"old_sha={old_sha or 'none'}\n")
            f.write(f"new_sha={new_sha}\n")
            f.write(f"old_version={old_version or 'none'}\n")
            f.write(f"new_version={new_version}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
