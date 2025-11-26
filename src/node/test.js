const pinpoint = require('./index');

async function runTests() {
    console.log("Testing validate()...");
    console.assert(pinpoint.validate("110001") === true, "110001 should be valid");
    console.assert(pinpoint.validate(110001) === true, "110001 (number) should be valid");
    console.assert(pinpoint.validate("999999") === false, "999999 should be invalid");
    console.log("PASS");

    console.log("Testing lookup()...");
    const details = await pinpoint.lookup("110001");
    console.assert(details.length > 0, "Should find details for 110001");
    const first = details[0];
    console.assert(first.office.includes("New Delhi") || first.office.includes("Connaught") || first.office.includes("Baroda"), "Should contain expected office name");
    console.log(`Found ${details.length} offices for 110001`);
    console.log("PASS");

    console.log("Testing searchDistricts()...");
    const districts = pinpoint.searchDistricts("Delhi");
    console.assert(districts.length > 0, "Should find Delhi districts");
    console.log(`Found districts: ${districts.slice(0, 5)}`);
    console.log("PASS");

    console.log("Testing findNearby()...");
    // CP coordinates
    const lat = 28.6304;
    const lng = 77.2177;
    const nearby = await pinpoint.findNearby(lat, lng, 2);
    console.assert(nearby.length > 0, "Should find nearby offices");
    console.log(`Found ${nearby.length} offices within 2km of CP`);
    if (nearby.length > 0) {
        console.log(` - ${nearby[0].office} (${nearby[0].distance_km} km)`);
    }
    console.log("PASS");
}

runTests().catch(err => {
    console.error("TEST FAILED:", err);
    process.exit(1);
});
