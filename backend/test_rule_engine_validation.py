from pydantic import ValidationError

from app.rule_engine.permission_rules import (
    PermissionRequestInput,
    evaluate_permission_request,
)


print("\n=== RULE ENGINE VALIDATION TESTS ===")

# Test 1: Valid request should be accepted
try:
    request = PermissionRequestInput(
        request_id="REQ-101",
        user_id="pilot001",
        flight_number="AI501",
        requested_action="TAKEOFF",
        identity_verified=True,
        permission_valid=True,
        operational_block=False,
    )

    print("Test 1 passed: Valid permission request accepted.")

except ValidationError as error:
    print("Test 1 failed:", error)


# Test 2: Missing required request_id should be rejected
try:
    PermissionRequestInput(
        user_id="pilot001",
        flight_number="AI501",
        requested_action="TAKEOFF",
        identity_verified=True,
        permission_valid=True,
        operational_block=False,
    )

    print("Test 2 failed: Missing request_id was accepted.")

except ValidationError:
    print("Test 2 passed: Missing request_id rejected.")


# Test 3: Invalid decision conditions should produce HOLD
try:
    request = PermissionRequestInput(
        request_id="REQ-102",
        user_id="pilot001",
        flight_number="AI502",
        requested_action="TAKEOFF",
        identity_verified=False,
        permission_valid=True,
        operational_block=False,
    )

    result = evaluate_permission_request(request)

    assert result.decision == "HOLD", (
        f"Expected HOLD, received {result.decision}"
    )

    print("Test 3 passed: Unverified identity produces HOLD.")

except (ValidationError, AssertionError) as error:
    print("Test 3 failed:", error)


# Test 4: Operational block should produce DELAY
try:
    request = PermissionRequestInput(
        request_id="REQ-103",
        user_id="pilot001",
        flight_number="AI503",
        requested_action="TAKEOFF",
        identity_verified=True,
        permission_valid=True,
        operational_block=True,
    )

    result = evaluate_permission_request(request)

    assert result.decision == "DELAY", (
        f"Expected DELAY, received {result.decision}"
    )

    print("Test 4 passed: Operational block produces DELAY.")

except (ValidationError, AssertionError) as error:
    print("Test 4 failed:", error)


print("\n=== VALIDATION TESTS FINISHED ===")