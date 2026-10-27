from pydantic import ValidationError

from app.rule_engine.scheduling import (
    RunwaySlot,
    detect_runway_conflict,
)


def main():

    print("\n=== RUNWAY CONFLICT TESTS ===")

    # Test 1: Overlapping time slots on the same runway.
    first = RunwaySlot(
        airport_code="HYD",
        flight_number="AI501",
        runway_id="RWY-09",
        start_minute=600,
        end_minute=630,
    )

    second = RunwaySlot(
        airport_code="HYD",
        flight_number="AI502",
        runway_id="RWY-09",
        start_minute=620,
        end_minute=650,
    )

    result = detect_runway_conflict(first, second)

    assert result.conflict_detected is True

    print("Test 1 passed: Overlapping runway slots detected.")
    print(result.model_dump())

    # Test 2: Non-overlapping time slots.
    first = RunwaySlot(
        airport_code="HYD",
        flight_number="AI501",
        runway_id="RWY-09",
        start_minute=600,
        end_minute=630,
    )

    second = RunwaySlot(
        airport_code="HYD",
        flight_number="AI502",
        runway_id="RWY-09",
        start_minute=630,
        end_minute=660,
    )

    result = detect_runway_conflict(first, second)

    assert result.conflict_detected is False

    print("Test 2 passed: Non-overlapping slots do not trigger a conflict.")

    # Test 3: Different runways.
    first = RunwaySlot(
        airport_code="HYD",
        flight_number="AI501",
        runway_id="RWY-09",
        start_minute=600,
        end_minute=630,
    )

    second = RunwaySlot(
        airport_code="HYD",
        flight_number="AI502",
        runway_id="RWY-27",
        start_minute=620,
        end_minute=650,
    )

    result = detect_runway_conflict(first, second)

    assert result.conflict_detected is False

    print("Test 3 passed: Different runways do not trigger this rule.")

    # Test 4: Different airports.
    first = RunwaySlot(
        airport_code="HYD",
        flight_number="AI501",
        runway_id="RWY-09",
        start_minute=600,
        end_minute=630,
    )

    second = RunwaySlot(
        airport_code="BLR",
        flight_number="AI502",
        runway_id="RWY-09",
        start_minute=620,
        end_minute=650,
    )

    result = detect_runway_conflict(first, second)

    assert result.conflict_detected is False

    print("Test 4 passed: Different airports are not compared for conflict.")

    # Test 5: Invalid time interval.
    try:
        RunwaySlot(
            airport_code="HYD",
            flight_number="AI503",
            runway_id="RWY-09",
            start_minute=650,
            end_minute=640,
        )

        raise AssertionError(
            "Invalid time interval should have been rejected."
        )

    except ValidationError:
        print("Test 5 passed: Invalid time interval rejected.")

    print("\nAll runway conflict tests passed.")


if __name__ == "__main__":
    main()