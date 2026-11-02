from datetime import datetime, timedelta, timezone

from app.database.flight_database import (
    initialize_flight_database,
    create_flight,
    get_flight_by_id,
    update_flight,
    delete_flight,
    calculate_flight_delay,
)

from app.schemas.flight import FlightCreate, FlightUpdate


def test_delay_calculation():

    scheduled = "2026-11-05T10:00:00+00:00"

    # Test 1: No delay
    assert calculate_flight_delay(
        scheduled,
        scheduled,
    ) == 0

    print("✓ No delay calculated correctly")

    # Test 2: 30-minute delay
    assert calculate_flight_delay(
        scheduled,
        "2026-11-05T10:30:00+00:00",
    ) == 30

    print("✓ 30-minute delay calculated correctly")

    # Test 3: 75-minute delay
    assert calculate_flight_delay(
        scheduled,
        "2026-11-05T11:15:00+00:00",
    ) == 75

    print("✓ 75-minute delay calculated correctly")

    # Test 4: Early departure
    assert calculate_flight_delay(
        scheduled,
        "2026-11-05T09:45:00+00:00",
    ) == 0

    print("✓ Early departure handled correctly")

    # Test 5: Actual departure takes priority
    assert calculate_flight_delay(
        scheduled,
        "2026-11-05T10:45:00+00:00",
        "2026-11-05T10:20:00+00:00",
    ) == 20

    print("✓ Actual departure priority verified")


def test_database_delay_update():

    initialize_flight_database()

    now = datetime.now(timezone.utc)

    scheduled = now + timedelta(hours=2)

    flight = FlightCreate(
        flight_number="TEST-DELAY-001",
        airline="Test Airline",
        origin_code="HYD",
        destination_code="DEL",
        scheduled_departure=scheduled,
        scheduled_arrival=scheduled + timedelta(hours=3),
        status="SCHEDULED",
    )

    created = create_flight(flight)

    flight_id = created["id"]

    try:
        assert created["delay_minutes"] == 0

        print("✓ Initial flight delay is zero")

        updated = update_flight(
            flight_id,
            FlightUpdate(
                status="DELAYED",
                estimated_departure=scheduled + timedelta(minutes=45),
            ),
        )

        assert updated["delay_minutes"] == 45

        print("✓ Database delay updated to 45 minutes")

        fetched = get_flight_by_id(flight_id)

        assert fetched["delay_minutes"] == 45

        print("✓ Calculated delay persisted in SQLite")

    finally:
        delete_flight(flight_id)

    print("✓ Test flight cleaned up")


if __name__ == "__main__":

    test_delay_calculation()

    test_database_delay_update()

    print("\nAll flight delay tests passed.")