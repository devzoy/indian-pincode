const assert = require('assert');
const pinpoint = require('./index');

async function runTests() {
    console.log("Testing validate()...");
    assert.strictEqual(pinpoint.validate("110001"), true, "110001 should be valid");
    assert.strictEqual(pinpoint.validate(110001), true, "110001 (number) should be valid");
    assert.strictEqual(pinpoint.validate("999999"), false, "999999 should be invalid");
    console.log("PASS");

    console.log("Testing lookup()...");
    const details = await pinpoint.lookup("110001");
    assert.ok(details.length > 0, "Should find details for 110001");
    const first = details[0];
    assert.ok(
        typeof first.office === "string" && first.office.length > 0,
        "office field should be a non-empty string"
    );
    console.log(`Found ${details.length} offices for 110001`);
    console.log("PASS");

    console.log("Testing searchDistricts()...");
    const districts = pinpoint.searchDistricts("Delhi");
    assert.ok(districts.length > 0, "Should find Delhi districts");
    console.log(`Found districts: ${districts.slice(0, 5)}`);
    console.log("PASS");

    console.log("Testing findNearby()...");
    // CP coordinates
    const lat = 28.6304;
    const lng = 77.2177;
    const nearby = await pinpoint.findNearby(lat, lng, 2);
    assert.ok(nearby.length > 0, "Should find nearby offices");
    const n0 = nearby[0];
    // The nearby result must carry a numeric `distance` field within the radius.
    assert.strictEqual(
        typeof n0.distance, "number",
        "nearby result must have a numeric 'distance' field"
    );
    assert.ok(
        n0.distance >= 0 && n0.distance <= 2,
        `nearest distance (${n0.distance}) should be within the 2km radius`
    );
    console.log(`Found ${nearby.length} offices within 2km of CP`);
    console.log(` - ${n0.office} (${n0.distance} km)`);
    console.log("PASS");
}

runTests()
    .then(() => console.log("\nALL TESTS PASSED"))
    .catch(err => {
        console.error("TEST FAILED:", err.message);
        process.exit(1);
    });
