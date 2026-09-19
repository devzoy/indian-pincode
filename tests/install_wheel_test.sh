#!/usr/bin/env bash
# Build the Python core + geo wheels and install them into a CLEAN venv (not the
# source tree), then import and exercise the packages. This proves the packaged
# data (importlib.resources) and read-only SQLite work from an installed wheel.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# 1. Generate package data from the canonical build.
python -m pipeline.build --emit-packages

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# 2. Build wheels.
python -m pip install --quiet --upgrade build
python -m build --wheel --outdir "$WORK/dist" packages/py-core
python -m build --wheel --outdir "$WORK/dist" packages/py-geo

# 3. Clean venv, install ONLY the wheels (no source path).
python -m venv "$WORK/venv"
"$WORK/venv/bin/pip" install --quiet --no-index --find-links "$WORK/dist" \
  indian-pincode indian-pincode-geo

# 4. Import from the installed location (cd out of the repo so src isn't picked up).
cd "$WORK"
"$WORK/venv/bin/python" - <<'PY'
import indian_pincode as core
import indian_pincode_geo as geo

assert core.validate("110001") is True
d = core.get_details("110025")
assert d["state"] == "DELHI" and "UTTAR PRADESH" in d["states"]
offices = geo.lookup("110001")
assert offices and offices[0]["office_type"] == "HO"
near = geo.find_nearby(28.63, 77.21, radius_km=5)
assert near and "distance_km" in near[0]
assert core.DATA_VERSION == geo.data_version()
print("clean-venv wheel install test: OK")
PY
