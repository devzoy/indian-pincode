"""`python -m pipeline.build --emit-packages` must be byte-deterministic:
running it twice on the same canonical build produces identical package data
(gzip mtime=0, sorted JSON keys, deterministic SQLite insert order)."""

import glob
import hashlib
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

from pipeline import config, emit  # noqa: E402

PACKAGE_DATA_GLOBS = [
    "packages/node-core/data/*",
    "packages/node-geo/data/*",
    "packages/py-core/indian_pincode/data/*",
    "packages/py-geo/indian_pincode_geo/data/*",
]


def _hash_all():
    result = {}
    for pat in PACKAGE_DATA_GLOBS:
        for path in sorted(glob.glob(os.path.join(REPO_ROOT, pat))):
            with open(path, "rb") as f:
                result[os.path.relpath(path, REPO_ROOT)] = hashlib.sha256(f.read()).hexdigest()
    return result


@pytest.mark.skipif(
    not os.path.exists(config.NORMALIZED_PATH),
    reason="canonical build not present; run the full pipeline first",
)
def test_emit_is_byte_deterministic():
    emit.emit_all()
    first = _hash_all()
    assert first, "no package data emitted"
    emit.emit_all()
    second = _hash_all()
    assert first == second, "emit is not deterministic: " + str(
        {k: (first[k], second[k]) for k in first if first[k] != second.get(k)}
    )
