from datetime import datetime, timedelta, timezone

from app.database.flight_database import (
    initialize_flight_database,
    create_flight,
    get_all_flights,
    get_flight_by_id,
    update_flight,
    delete_flight,
)

from app.schemas.flight import FlightCreate, FlightUpdate


def test_flight_crud():

    initialize_flight_database()

    now = datetime.now(timezone.utc)

    # CREATE
    flight = FlightCreate(
        flight_number="TEST001",
        airline="Test Airline",
        origin_code="HYD",
        destination_code="DEL",
        scheduled_departure=now + timedelta(hours=2),
        scheduled_arrival=now + timedelta(hours=4),
        status="SCHEDULED",
    )

    created = create_flight(flight)

    flight_id = created["id"]

    print("✓ Flight created:", flight_id)

    try:
        # READ BY ID
        fetched = get_flight_by_id(flight_id)

        assert fetched is not None
        assert fetched["flight_number"] == "TEST001"

        print("✓ Flight retrieved by ID")

        # READ ALL
        flights = get_all_flights()

        assert any(
            item["id"] == flight_id
            for item in flights
        )

        print("✓ Flight retrieved from flight list")

        # UPDATE
        updated = update_flight(
            flight_id,
            FlightUpdate(status="DELAYED"),
        )

        assert updated is not None
        assert updated["status"] == "DELAYED"

        print("✓ Flight updated")

    finally:
        # DELETE — clean up test data
        deleted = delete_flight(flight_id)

        assert deleted is True

        print("✓ Test flight deleted")

    assert get_flight_by_id(flight_id) is None

    print("\nAll Flight CRUD tests passed.")


if __name__ == "__main__":
    test_flight_crud()