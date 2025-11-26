import sys
import os
import json

# Ensure we can import indian_pincode
sys.path.insert(0, os.path.abspath("src/python"))

import indian_pincode as pinpoint

def test_validate():
    print("Testing validate()...")
    assert pinpoint.validate("110001") == True
    assert pinpoint.validate(110001) == True
    assert pinpoint.validate("999999") == False
    assert pinpoint.validate("abc") == False
    print("PASS")

def test_lookup():
    print("Testing lookup()...")
    print(f"DB Path in lib: {pinpoint._DB_PATH}")
    print(f"DB Exists: {os.path.exists(pinpoint._DB_PATH)}")
    details = pinpoint.lookup("110001")
    print(f"Lookup result for 110001: {len(details)} offices")
    assert len(details) > 0
    # Check if any office matches expected names
    found_expected = False
    for office in details:
        name = office['office_name']
        if "New Delhi" in name or "Connaught Place" in name or "Parliament" in name or "Baroda House" in name:
            found_expected = True
            break
    assert found_expected, "Did not find expected office names in 110001"
    print(f"Found {len(details)} offices for 110001")
    print("PASS")

def test_search_districts():
    print("Testing search_districts()...")
    results = pinpoint.search_districts("Delhi")
    assert len(results) > 0
    print(f"Found districts: {results[:5]}...")
    assert "New Delhi" in results or "Central Delhi" in results or "North Delhi" in results or "South Delhi" in results or any("DELHI" in r.upper() for r in results)
    print("PASS")

def test_find_nearby():
    print("Testing find_nearby()...")
    # Connaught Place coordinates approx
    lat, lng = 28.6304, 77.2177
    nearby = pinpoint.find_nearby(lat, lng, radius_km=2.0)
    assert len(nearby) > 0
    print(f"Found {len(nearby)} offices within 2km of CP")
    for n in nearby[:3]:
        print(f" - {n['office_name']} ({n['pincode']}): {n['distance_km']} km")
    print("PASS")

if __name__ == "__main__":
    try:
        test_validate()
        test_lookup()
        test_search_districts()
        test_find_nearby()
        print("\nALL TESTS PASSED")
    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)
