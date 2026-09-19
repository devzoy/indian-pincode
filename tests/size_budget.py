#!/usr/bin/env python3
"""Fail if any package exceeds its size budget. Measures from REAL artifacts:
  - npm: `npm pack --dry-run --json` unpacked size
  - PyPI: unpacked size of the built wheel's contents

Budgets (unpacked):
  core npm   <= 300 KB
  core PyPI  <= 300 KB
  geo npm    <= 6 MB
  geo PyPI   <= 10 MB

Assumes package data is already emitted and Node dist is built.
"""

from __future__ import annotations

import glob
import json
import os
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KB = 1024
MB = 1024 * 1024

BUDGETS = {
    "npm core": 300 * KB,
    "npm geo": 6 * MB,
    "pypi core": 300 * KB,
    "pypi geo": 10 * MB,
}


def npm_unpacked(pkg_dir: str) -> int:
    out = subprocess.check_output(
        ["npm", "pack", "--dry-run", "--json"], cwd=os.path.join(ROOT, pkg_dir)
    )
    info = json.loads(out)[0]
    return int(info["unpackedSize"])


def wheel_unpacked(pkg_dir: str) -> int:
    dist = os.path.join(ROOT, pkg_dir, "dist")
    os.makedirs(dist, exist_ok=True)
    for f in glob.glob(os.path.join(dist, "*.whl")):
        os.remove(f)
    subprocess.check_call(
        [sys.executable, "-m", "build", "--wheel", "--outdir", dist, os.path.join(ROOT, pkg_dir)],
        stdout=subprocess.DEVNULL,
    )
    wheels = glob.glob(os.path.join(dist, "*.whl"))
    assert wheels, f"no wheel built for {pkg_dir}"
    total = 0
    with zipfile.ZipFile(wheels[0]) as z:
        for zi in z.infolist():
            total += zi.file_size
    return total


def main():
    sizes = {
        "npm core": npm_unpacked("packages/node-core"),
        "npm geo": npm_unpacked("packages/node-geo"),
        "pypi core": wheel_unpacked("packages/py-core"),
        "pypi geo": wheel_unpacked("packages/py-geo"),
    }
    failures = []
    for name, size in sizes.items():
        budget = BUDGETS[name]
        status = "OK" if size <= budget else "OVER"
        print(f"  {name:10s} {size/KB:9.1f} KB  (budget {budget/KB:.0f} KB)  {status}")
        if size > budget:
            failures.append(f"{name}: {size/KB:.1f} KB > {budget/KB:.0f} KB")
    if failures:
        print("SIZE BUDGET EXCEEDED:")
        for f in failures:
            print("  -", f)
        return 1
    print("all packages within budget")
    return 0


if __name__ == "__main__":
    sys.exit(main())
