"""All 4 package manifests must carry the single source-of-truth version, and
their cross-package dependency pins must be exact."""

import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

from scripts import propagate_version as pv  # noqa: E402


def _version():
    with open(os.path.join(REPO_ROOT, "version.json"), encoding="utf-8") as f:
        return json.load(f)["version"]


def test_propagate_check_passes():
    # The committed manifests must already match version.json.
    assert pv.apply(_version(), check=True) is True


def test_all_four_manifests_have_same_version():
    v = _version()
    nc = json.load(open(os.path.join(REPO_ROOT, "packages/node-core/package.json")))
    ng = json.load(open(os.path.join(REPO_ROOT, "packages/node-geo/package.json")))
    assert nc["version"] == v
    assert ng["version"] == v
    assert ng["dependencies"]["@devzoy/indian-pincode"] == v  # exact, not a range
    assert "peerDependencies" not in ng

    pc = open(os.path.join(REPO_ROOT, "packages/py-core/pyproject.toml")).read()
    pg = open(os.path.join(REPO_ROOT, "packages/py-geo/pyproject.toml")).read()
    assert re.search(rf'(?m)^version\s*=\s*"{re.escape(v)}"', pc)
    assert re.search(rf'(?m)^version\s*=\s*"{re.escape(v)}"', pg)
    assert f"indian-pincode-geo=={v}" in pc      # core [geo] extra pins geo exactly
    assert f"indian-pincode=={v}" in pg          # geo requires core exactly
