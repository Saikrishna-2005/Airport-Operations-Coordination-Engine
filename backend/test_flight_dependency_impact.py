from datetime import datetime, timedelta, timezone

from app.database.flight_database import (
    initialize_flight_database,
    create_flight,
    delete_flight,
    create_flight_dependency,
    delete_flight_dependency,
    calculate_flight_dependency_impacts,
)

from app.schemas.flight import FlightCreate


def test_dependency_impact():

    initialize_flight_database()

    # Use future UTC timestamps for testing
    now = datetime.now(timezone.utc)

    first_departure = now + timedelta(hours=2)
    first_arrival = first_departure + timedelta(hours=2)

    second_departure = first_arrival + timedelta(minutes=60)
    second_arrival = second_departure + timedelta(hours=2)

    first_id = None
    second_id = None
    dependency_id = None

    try:
        # ====================================================
        # CREATE FIRST FLIGHT
        # ====================================================

        first = create_flight(
            FlightCreate(
                flight_number="TEST-IMPACT-001",
                airline="Test Airline",
                origin_code="HYD",
                destination_code="DEL",
                scheduled_departure=first_departure,
                scheduled_arrival=first_arrival,
                estimated_arrival=first_arrival,
            )
        )

        first_id = first["id"]

        # ====================================================
        # CREATE SECOND FLIGHT
        # ====================================================

        second = create_flight(
            FlightCreate(
                flight_number="TEST-IMPACT-002",
                airline="Test Airline",
                origin_code="DEL",
                destination_code="HYD",
                scheduled_departure=second_departure,
                scheduled_arrival=second_arrival,
            )
        )

        second_id = second["id"]

        # ====================================================
        # CREATE AIRCRAFT DEPENDENCY
        # ====================================================

        dependency = create_flight_dependency(
            flight_id=first_id,
            dependent_flight_id=second_id,
            dependency_type="AIRCRAFT",
            minimum_turnaround_minutes=45,
        )

        dependency_id = dependency["id"]

        print("✓ Aircraft dependency created")

        # ====================================================
        # TEST 1 — NO ADDITIONAL DELAY
        # ====================================================

        impacts = calculate_flight_dependency_impacts(
            flight_id=first_id,
            additional_delay_minutes=0,
        )

        assert len(impacts) == 1
        assert impacts[0]["impact_minutes"] == 0

        print("✓ No impact when turnaround is sufficient")

        # ====================================================
        # TEST 2 — 45-MINUTE SOURCE ARRIVAL DELAY
        # ====================================================

        impacts = calculate_flight_dependency_impacts(
            flight_id=first_id,
            additional_delay_minutes=45,
        )

        assert impacts[0]["impact_minutes"] == 30
        assert impacts[0]["impact_status"] == "AFFECTED"

        print("✓ 30-minute dependent flight impact calculated")

        # ====================================================
        # TEST 3 — 90-MINUTE SOURCE ARRIVAL DELAY
        # ====================================================

        impacts = calculate_flight_dependency_impacts(
            flight_id=first_id,
            additional_delay_minutes=90,
        )

        assert impacts[0]["impact_minutes"] == 75

        print("✓ 75-minute dependent flight impact calculated")

    finally:

        if dependency_id is not None:
            delete_flight_dependency(dependency_id)

        if second_id is not None:
            delete_flight(second_id)

        if first_id is not None:
            delete_flight(first_id)

        print("✓ Test records cleaned up")

    print("\nAll Flight Dependency Impact tests passed.")


if __name__ == "__main__":
    test_dependency_impact()