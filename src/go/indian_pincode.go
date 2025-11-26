package indian_pincode

import (
	"embed"
	"encoding/json"
	"fmt"
	"math"
	"sort"
	"strconv"
	"strings"
)

//go:embed data/*
var dataFS embed.FS

// PincodeDetails represents the details of a post office
type PincodeDetails struct {
	Office     string  `json:"office"`
	Type       string  `json:"type"`
	Delivery   string  `json:"delivery"`
	Division   string  `json:"division"`
	Region     string  `json:"region"`
	Circle     string  `json:"circle"`
	Taluk      string  `json:"taluk"`
	District   string  `json:"district"`
	State      string  `json:"state"`
	Lat        string  `json:"lat"`
	Lng        string  `json:"lng"`
	DistanceKm float64 `json:"distance_km,omitempty"`
}

// ValidationData map prefix -> list of suffixes
type ValidationData map[string][]int

var (
	validationData ValidationData
	districtsData  []string
	geoData        [][]float64 // [pincode, lat, lng]
)

func init() {
	// Load validation data
	file, _ := dataFS.ReadFile("data/pincodes.compressed.json")
	json.Unmarshal(file, &validationData)

	// Load districts
	file, _ = dataFS.ReadFile("data/districts.json")
	json.Unmarshal(file, &districtsData)

	// Load geo data
	file, _ = dataFS.ReadFile("data/geo.json")
	json.Unmarshal(file, &geoData)
}

// Validate checks if a pincode exists
func Validate(pincode string) bool {
	pincode = strings.TrimSpace(pincode)
	if len(pincode) != 6 {
		return false
	}
	prefix := pincode[:3]
	suffix, err := strconv.Atoi(pincode[3:])
	if err != nil {
		return false
	}

	if list, ok := validationData[prefix]; ok {
		// Binary search could be faster, but linear scan is okay for small lists
		for _, s := range list {
			if s == suffix {
				return true
			}
		}
	}
	return false
}

// Lookup returns details for a pincode
func Lookup(pincode string) ([]PincodeDetails, error) {
	if !Validate(pincode) {
		return nil, fmt.Errorf("invalid pincode")
	}

	prefix := pincode[:3]
	filename := fmt.Sprintf("data/details/%s.json", prefix)
	
	file, err := dataFS.ReadFile(filename)
	if err != nil {
		return nil, err
	}

	var chunk map[string][]PincodeDetails
	if err := json.Unmarshal(file, &chunk); err != nil {
		return nil, err
	}

	if details, ok := chunk[pincode]; ok {
		return details, nil
	}
	return nil, fmt.Errorf("pincode not found")
}

// SearchDistricts searches for districts
func SearchDistricts(query string) []string {
	query = strings.ToLower(strings.TrimSpace(query))
	if query == "" {
		return nil
	}

	var results []string
	for _, d := range districtsData {
		if strings.Contains(strings.ToLower(d), query) {
			results = append(results, d)
		}
	}
	return results
}

func toRad(d float64) float64 {
	return d * math.Pi / 180
}

func haversine(lat1, lon1, lat2, lon2 float64) float64 {
	const R = 6371 // km
	dLat := toRad(lat2 - lat1)
	dLon := toRad(lon2 - lon1)
	a := math.Sin(dLat/2)*math.Sin(dLat/2) +
		math.Cos(toRad(lat1))*math.Cos(toRad(lat2))*
			math.Sin(dLon/2)*math.Sin(dLon/2)
	c := 2 * math.Atan2(math.Sqrt(a), math.Sqrt(1-a))
	return R * c
}

// FindNearby finds pincodes within radius
func FindNearby(lat, lng, radiusKm float64) ([]PincodeDetails, error) {
	var nearby []struct {
		Pincode  string
		Distance float64
	}

	for _, point := range geoData {
		// point is [pincode, lat, lng]
		p := int(point[0])
		pLat := point[1]
		pLng := point[2]

		dist := haversine(lat, lng, pLat, pLng)
		if dist <= radiusKm {
			nearby = append(nearby, struct {
				Pincode  string
				Distance float64
			}{
				Pincode:  fmt.Sprintf("%06d", p),
				Distance: math.Round(dist*100) / 100,
			})
		}
	}

	sort.Slice(nearby, func(i, j int) bool {
		return nearby[i].Distance < nearby[j].Distance
	})

	var results []PincodeDetails
	for _, item := range nearby {
		details, err := Lookup(item.Pincode)
		if err == nil {
			for i := range details {
				details[i].DistanceKm = item.Distance
			}
			results = append(results, details...)
		}
	}

	return results, nil
}
