from datetime import datetime, timedelta, timezone

from app.database.flight_database import (
    initialize_flight_database,
    create_flight,
    delete_flight,
    create_flight_dependency,
    get_flight_dependencies,
    delete_flight_dependency,
)

from app.schemas.flight import FlightCreate


def test_flight_dependencies():

    initialize_flight_database()

    now = datetime.now(timezone.utc)

    first_departure = now + timedelta(hours=2)

    first = create_flight(
        FlightCreate(
            flight_number="TEST-DEP-001",
            airline="Test Airline",
            origin_code="HYD",
            destination_code="DEL",
            scheduled_departure=first_departure,
            scheduled_arrival=(
                first_departure + timedelta(hours=2)
            ),
        )
    )

    first_id = first["id"]
    second_id = None
    dependency_id = None

    try:
        second_departure = (
            first_departure + timedelta(hours=3)
        )

        second = create_flight(
            FlightCreate(
                flight_number="TEST-DEP-002",
                airline="Test Airline",
                origin_code="DEL",
                destination_code="HYD",
                scheduled_departure=second_departure,
                scheduled_arrival=(
                    second_departure + timedelta(hours=2)
                ),
            )
        )

        second_id = second["id"]

        # TEST 1 — CREATE DEPENDENCY
        dependency = create_flight_dependency(
            flight_id=first_id,
            dependent_flight_id=second_id,
            dependency_type="AIRCRAFT",
            minimum_turnaround_minutes=45,
        )

        dependency_id = dependency["id"]

        assert dependency["dependency_type"] == "AIRCRAFT"

        print("✓ Flight dependency created")

        # TEST 2 — RETRIEVE DEPENDENCY
        dependencies = get_flight_dependencies(first_id)

        assert len(dependencies) == 1

        assert (
            dependencies[0]["dependent_flight_id"]
            == second_id
        )

        print("✓ Flight dependency retrieved")

        # TEST 3 — PREVENT DUPLICATES
        try:
            create_flight_dependency(
                first_id,
                second_id,
                "AIRCRAFT",
                45,
            )

            raise AssertionError(
                "Duplicate dependency was accepted"
            )

        except ValueError as exc:
            assert "already exists" in str(exc)

        print("✓ Duplicate dependency rejected")

        # TEST 4 — PREVENT CYCLES
        try:
            create_flight_dependency(
                second_id,
                first_id,
                "AIRCRAFT",
                45,
            )

            raise AssertionError(
                "Cyclic dependency was accepted"
            )

        except ValueError as exc:
            assert "cycle" in str(exc)

        print("✓ Cyclic dependency rejected")

        # TEST 5 — DELETE DEPENDENCY
        assert delete_flight_dependency(dependency_id)

        dependency_id = None

        assert get_flight_dependencies(first_id) == []

        print("✓ Flight dependency deleted")

    finally:
        if dependency_id is not None:
            delete_flight_dependency(dependency_id)

        if second_id is not None:
            delete_flight(second_id)

        delete_flight(first_id)

        print("✓ Test flights cleaned up")

    print("\nAll Flight Dependency tests passed.")


if __name__ == "__main__":
    test_flight_dependencies()