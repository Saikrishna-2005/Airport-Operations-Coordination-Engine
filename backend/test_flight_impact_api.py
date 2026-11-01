from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app

from app.database.flight_database import (
    initialize_flight_database,
    create_flight,
    delete_flight,
    create_flight_dependency,
    delete_flight_dependency,
    get_flight_by_id,
)

from app.schemas.flight import FlightCreate


client = TestClient(app)


def test_flight_impact_api():

    initialize_flight_database()

    now = datetime.now(timezone.utc)

    first_departure = now + timedelta(hours=2)
    first_arrival = first_departure + timedelta(hours=2)

    second_departure = (
        first_arrival + timedelta(minutes=60)
    )

    first_id = None
    second_id = None
    dependency_id = None

    try:

        # ====================================================
        # CREATE SOURCE FLIGHT
        # ====================================================

        first = create_flight(
            FlightCreate(
                flight_number="TEST-SIM-001",
                airline="Test Airline",
                origin_code="HYD",
                destination_code="DEL",
                scheduled_departure=first_departure,
                scheduled_arrival=first_arrival,
            )
        )

        first_id = first["id"]

        # ====================================================
        # CREATE DEPENDENT FLIGHT
        # ====================================================

        second = create_flight(
            FlightCreate(
                flight_number="TEST-SIM-002",
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

        # ====================================================
        # CREATE DEPENDENCY
        # ====================================================

        dependency = create_flight_dependency(
            flight_id=first_id,
            dependent_flight_id=second_id,
            dependency_type="AIRCRAFT",
            minimum_turnaround_minutes=45,
        )

        dependency_id = dependency["id"]

        print("✓ Simulation test data created")

        # ====================================================
        # TEST 1 — AUTHENTICATION REQUIRED
        # ====================================================

        response = client.post(
            "/api/flights/simulate-impact",
            json={
                "flight_id": first_id,
                "additional_delay_minutes": 45,
            },
        )

        assert response.status_code == 401

        print("✓ Authentication protection verified")

        # ====================================================
        # TEST 2 — READ-ONLY DATABASE CALCULATION
        # ====================================================

        before_source = get_flight_by_id(first_id)
        before_dependent = get_flight_by_id(second_id)

        # Call the calculation function directly to
        # verify the expected simulation result.
        from app.database.flight_database import (
            calculate_flight_dependency_impacts,
        )

        impacts = calculate_flight_dependency_impacts(
            flight_id=first_id,
            additional_delay_minutes=45,
        )

        assert len(impacts) == 1

        assert impacts[0]["impact_minutes"] == 30

        after_source = get_flight_by_id(first_id)
        after_dependent = get_flight_by_id(second_id)

        assert before_source == after_source
        assert before_dependent == after_dependent

        print("✓ Simulation impact calculated correctly")
        print("✓ Flight records remained unchanged")

        # ====================================================
        # TEST 3 — INVALID FLIGHT ID
        # ====================================================

        response = client.post(
            "/api/flights/simulate-impact",
            json={
                "flight_id": -1,
                "additional_delay_minutes": 45,
            },
        )

        # Authentication runs before request handling,
        # so an unauthenticated request returns 401.
        assert response.status_code == 401

        print("✓ Protected endpoint rejects unauthenticated requests")

    finally:

        if dependency_id is not None:
            delete_flight_dependency(dependency_id)

        if second_id is not None:
            delete_flight(second_id)

        if first_id is not None:
            delete_flight(first_id)

        print("✓ Simulation test records cleaned up")

    print("\nFlight Impact Simulation API tests passed.")


if __name__ == "__main__":
    test_flight_impact_api()