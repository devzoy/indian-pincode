#!/usr/bin/env python3
"""Bump version.json (default: patch) and propagate to all 4 package manifests.

Usage:
  python scripts/bump_version.py [patch|minor|major]
Prints the new version to stdout (and to $GITHUB_OUTPUT as new_version=... if set).
"""

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION_JSON = os.path.join(ROOT, "version.json")


def _bump(version: str, part: str) -> str:
    major, minor, patch = (int(x) for x in version.split("."))
    if part == "major":
        major, minor, patch = major + 1, 0, 0
    elif part == "minor":
        minor, patch = minor + 1, 0
    else:
        patch += 1
    return f"{major}.{minor}.{patch}"


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    part = argv[0] if argv else "patch"
    with open(VERSION_JSON, encoding="utf-8") as f:
        data = json.load(f)
    new = _bump(data["version"], part)
    data["version"] = new
    with open(VERSION_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    # Propagate into all 4 manifests.
    sys.path.insert(0, ROOT)
    from scripts import propagate_version
    propagate_version.apply(new, check=False)

    print(new)
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"new_version={new}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
