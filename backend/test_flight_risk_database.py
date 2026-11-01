from datetime import datetime, timedelta, timezone

from app.database.connection import get_db_connection

from app.database.flight_database import (
    initialize_flight_database,
    create_flight,
    get_flight_by_id,
    update_flight,
    delete_flight,
)

from app.schemas.flight import (
    FlightCreate,
    FlightUpdate,
)


def test_flight_risk_database():

    initialize_flight_database()

    now = datetime.now(timezone.utc)

    scheduled = now + timedelta(hours=2)

    flight = FlightCreate(
        flight_number="TEST-RISK-001",
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
        # TEST 1 — INITIAL RISK
        # ====================================================

        assert created["risk_score"] == 0

        print("✓ Initial flight risk calculated")

        # ====================================================
        # TEST 2 — UPDATE DELAY AND STATUS
        # ====================================================

        updated = update_flight(
            flight_id,
            FlightUpdate(
                status="DELAYED",
                estimated_departure=(
                    scheduled + timedelta(minutes=75)
                ),
            ),
        )

        assert updated["delay_minutes"] == 75

        assert updated["risk_score"] == 55

        print("✓ Flight risk updated to 55")

        # ====================================================
        # TEST 3 — VERIFY RISK FACTORS
        # ====================================================

        connection = get_db_connection()

        try:

            factors = connection.execute(
                """
                SELECT *
                FROM flight_risk_factors
                WHERE flight_id = ?
                ORDER BY id
                """,
                (flight_id,),
            ).fetchall()

            assert len(factors) == 2

            factor_types = {
                factor["factor_type"]
                for factor in factors
            }

            assert factor_types == {
                "DEPARTURE_DELAY",
                "FLIGHT_STATUS",
            }

            print("✓ Risk factors saved in SQLite")

        finally:

            connection.close()

        # ====================================================
        # TEST 4 — REMOVE DELAY
        # ====================================================

        updated = update_flight(
            flight_id,
            FlightUpdate(
                status="SCHEDULED",
                estimated_departure=scheduled,
            ),
        )

        assert updated["delay_minutes"] == 0

        assert updated["risk_score"] == 0

        print("✓ Flight risk recalculated to zero")

        # ====================================================
        # TEST 5 — VERIFY OLD FACTORS REMOVED
        # ====================================================

        connection = get_db_connection()

        try:

            factors = connection.execute(
                """
                SELECT *
                FROM flight_risk_factors
                WHERE flight_id = ?
                """,
                (flight_id,),
            ).fetchall()

            assert len(factors) == 0

            print("✓ Outdated risk factors removed")

        finally:

            connection.close()

        # ====================================================
        # TEST 6 — VERIFY PERSISTENCE
        # ====================================================

        fetched = get_flight_by_id(flight_id)

        assert fetched["risk_score"] == 0

        print("✓ Updated risk persisted in SQLite")

    finally:

        delete_flight(flight_id)

        print("✓ Test flight cleaned up")

    print(
        "\nAll Flight Risk Database integration tests passed."
    )


if __name__ == "__main__":
    test_flight_risk_database()