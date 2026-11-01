from datetime import datetime, timedelta, timezone

from app.database.flight_database import (
    initialize_flight_database,
    create_flight,
    update_flight,
    delete_flight,
    get_flight_operational_pulse,
)

from app.schemas.flight import (
    FlightCreate,
    FlightUpdate,
)


def test_operational_pulse():

    initialize_flight_database()

    now = datetime.now(timezone.utc)

    scheduled = now + timedelta(hours=2)

    # Capture existing database statistics
    before = get_flight_operational_pulse()

    flight = FlightCreate(
        flight_number="TEST-PULSE-001",
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

        # ====================================================
        # TEST 1 — TOTAL FLIGHT COUNT
        # ====================================================

        pulse = get_flight_operational_pulse()

        assert (
            pulse["total_flights"]
            == before["total_flights"] + 1
        )

        print("✓ Total flight count updated")

        # ====================================================
        # TEST 2 — SCHEDULED FLIGHT COUNT
        # ====================================================

        assert (
            pulse["scheduled_flights"]
            == before["scheduled_flights"] + 1
        )

        print("✓ Scheduled flight count updated")

        # ====================================================
        # TEST 3 — UPDATE FLIGHT TO DELAYED
        # ====================================================

        update_flight(
            flight_id,
            FlightUpdate(
                status="DELAYED",
                estimated_departure=(
                    scheduled + timedelta(minutes=60)
                ),
            ),
        )

        pulse = get_flight_operational_pulse()

        assert (
            pulse["delayed_flights"]
            == before["delayed_flights"] + 1
        )

        assert (
            pulse["scheduled_flights"]
            == before["scheduled_flights"]
        )

        print("✓ Delayed flight count updated")

        # ====================================================
        # TEST 4 — AVERAGE DELAY
        # ====================================================

        assert pulse["average_delay_minutes"] >= 0

        print("✓ Average flight delay calculated")

        # ====================================================
        # TEST 5 — CRITICAL RISK COUNT
        # ====================================================

        assert pulse["critical_risk_flights"] >= 0

        print("✓ Critical risk count calculated")

    finally:

        delete_flight(flight_id)

        print("✓ Test flight cleaned up")

    print("\nAll Operational Pulse tests passed.")


if __name__ == "__main__":
    test_operational_pulse()
    