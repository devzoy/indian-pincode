package indian_pincode

import (
	"testing"
)

func TestValidate(t *testing.T) {
	if !Validate("110001") {
		t.Error("110001 should be valid")
	}
	if Validate("999999") {
		t.Error("999999 should be invalid")
	}
}

func TestLookup(t *testing.T) {
	details, err := Lookup("110001")
	if err != nil {
		t.Errorf("Lookup failed: %v", err)
	}
	if len(details) == 0 {
		t.Error("Should find details")
	}
	found := false
	for _, d := range details {
		if d.Office == "Connaught Place SO" || d.Office == "New Delhi GPO" {
			found = true
			break
		}
	}
	if !found {
		t.Error("Expected office not found")
	}
}

func TestSearchDistricts(t *testing.T) {
	results := SearchDistricts("Delhi")
	if len(results) == 0 {
		t.Error("Should find districts")
	}
	found := false
	for _, r := range results {
		if r == "NEW DELHI" {
			found = true
			break
		}
	}
	if !found {
		t.Error("NEW DELHI not found in search")
	}
}

func TestFindNearby(t *testing.T) {
	// CP
	results, err := FindNearby(28.6304, 77.2177, 2.0)
	if err != nil {
		t.Errorf("FindNearby failed: %v", err)
	}
	if len(results) == 0 {
		t.Error("Should find nearby offices")
	}
	if results[0].DistanceKm > 2.0 {
		t.Error("Distance incorrect")
	}
}
