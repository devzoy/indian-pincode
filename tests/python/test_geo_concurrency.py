"""The read-only SQLite geo connection must be safe under concurrent reads."""

import os
import sys
import threading

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "packages", "py-core"))
sys.path.insert(0, os.path.join(REPO_ROOT, "packages", "py-geo"))

import indian_pincode_geo as geo  # noqa: E402


def test_concurrent_lookup_and_find_nearby():
    geo.preload()
    pins = ["110001", "560095", "700001", "400001", "380001", "682555", "744101"]
    pts = [(28.63, 77.21), (12.93, 77.62), (19.07, 72.87), (13.08, 80.27)]
    errors = []

    def worker(n):
        try:
            for i in range(200):
                assert len(geo.lookup(pins[i % len(pins)])) >= 0
                la, lo = pts[i % len(pts)]
                res = geo.find_nearby(la, lo, radius_km=5)
                assert isinstance(res, list)
                geo.reverse_lookup(la, lo)
        except Exception as e:  # noqa: BLE001
            errors.append(repr(e))

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"concurrent access errors: {errors[:3]}"


def test_lookup_stable_under_threads():
    geo.preload()
    baseline = [o["office_name"] for o in geo.lookup("110001")]
    results = []

    def worker():
        results.append([o["office_name"] for o in geo.lookup("110001")])

    threads = [threading.Thread(target=worker) for _ in range(16)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    for r in results:
        assert r == baseline
