#!/usr/bin/env python3
"""Propagate the single source-of-truth version (version.json) into all 4 package
manifests and their cross-package dependency pins.

Usage:
  python scripts/propagate_version.py          # write versions
  python scripts/propagate_version.py --check   # verify all match (exit 1 if not)

Manifests:
  packages/node-core/package.json               version
  packages/node-geo/package.json                version + dependencies["@devzoy/indian-pincode"]
  packages/py-core/pyproject.toml               version + [geo] extra pin indian-pincode-geo==X
  packages/py-geo/pyproject.toml                version + dependency indian-pincode==X
"""

from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _version() -> str:
    with open(os.path.join(ROOT, "version.json"), encoding="utf-8") as f:
        return json.load(f)["version"]


def _node_core_path():
    return os.path.join(ROOT, "packages", "node-core", "package.json")


def _node_geo_path():
    return os.path.join(ROOT, "packages", "node-geo", "package.json")


def _py_core_path():
    return os.path.join(ROOT, "packages", "py-core", "pyproject.toml")


def _py_geo_path():
    return os.path.join(ROOT, "packages", "py-geo", "pyproject.toml")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def apply(version: str, check: bool) -> bool:
    ok = True

    # --- node-core: version ---
    p = _node_core_path()
    m = json.loads(_read(p))
    if check:
        ok &= _expect(m["version"], version, f"{p} version")
    else:
        m["version"] = version
        _write(p, json.dumps(m, indent=2) + "\n")

    # --- node-geo: version + dependency on core (exact) ---
    p = _node_geo_path()
    m = json.loads(_read(p))
    dep = m.get("dependencies", {}).get("@devzoy/indian-pincode")
    if check:
        ok &= _expect(m["version"], version, f"{p} version")
        ok &= _expect(dep, version, f"{p} dependencies[@devzoy/indian-pincode]")
    else:
        m["version"] = version
        m.setdefault("dependencies", {})["@devzoy/indian-pincode"] = version
        m.pop("peerDependencies", None)
        _write(p, json.dumps(m, indent=2) + "\n")

    # --- py-core: version + [geo] extra pin ---
    p = _py_core_path()
    text = _read(p)
    if check:
        ok &= _expect(_toml_version(text), version, f"{p} version")
        ok &= _expect(_extra_pin(text, "indian-pincode-geo"), version, f"{p} [geo] extra pin")
    else:
        text = _set_toml_version(text, version)
        text = _set_extra_pin(text, "indian-pincode-geo", version)
        _write(p, text)

    # --- py-geo: version + dependency on core ---
    p = _py_geo_path()
    text = _read(p)
    if check:
        ok &= _expect(_toml_version(text), version, f"{p} version")
        ok &= _expect(_dep_pin(text, "indian-pincode"), version, f"{p} dependency pin")
    else:
        text = _set_toml_version(text, version)
        text = _set_dep_pin(text, "indian-pincode", version)
        _write(p, text)

    return ok


def _expect(actual, expected, label):
    if actual == expected:
        return True
    print(f"MISMATCH: {label}: {actual!r} != {expected!r}")
    return False


# ---- minimal TOML string surgery (avoids a toml dependency) ----------------

def _toml_version(text):
    m = re.search(r'(?m)^version\s*=\s*"([^"]+)"', text)
    return m.group(1) if m else None


def _set_toml_version(text, version):
    return re.sub(r'(?m)^(version\s*=\s*)"[^"]+"', rf'\g<1>"{version}"', text, count=1)


def _extra_pin(text, pkg):
    m = re.search(rf'{re.escape(pkg)}==([0-9][^"\']+)', text)
    return m.group(1) if m else None


def _set_extra_pin(text, pkg, version):
    return re.sub(rf'({re.escape(pkg)}==)[0-9][^"\']+', rf'\g<1>{version}', text)


def _dep_pin(text, pkg):
    m = re.search(rf'{re.escape(pkg)}==([0-9][^"\']+)', text)
    return m.group(1) if m else None


def _set_dep_pin(text, pkg, version):
    return re.sub(rf'({re.escape(pkg)}==)[0-9][^"\']+', rf'\g<1>{version}', text)


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    check = "--check" in argv
    version = _version()
    ok = apply(version, check)
    if check:
        if ok:
            print(f"OK: all 4 packages at version {version}")
            return 0
        return 1
    print(f"propagated version {version} to all 4 packages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
