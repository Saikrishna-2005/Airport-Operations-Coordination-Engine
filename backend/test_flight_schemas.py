from datetime import datetime, timezone, timedelta

from pydantic import ValidationError

from app.schemas.flight import (
    FlightCreate,
    FlightSimulationRequest,
)


def test_flight_schemas():

    now = datetime.now(timezone.utc)

    flight = FlightCreate(
        flight_number="AI305",
        airline="Air India",
        origin_code="HYD",
        origin_name="Hyderabad",
        destination_code="DEL",
        destination_name="Delhi",
        scheduled_departure=now + timedelta(hours=2),
        scheduled_arrival=now + timedelta(hours=4),
        status="SCHEDULED",
    )

    assert flight.flight_number == "AI305"

    assert flight.status == "SCHEDULED"

    print("✓ Flight creation schema validated")

    simulation = FlightSimulationRequest(
        flight_id=1,
        additional_delay_minutes=30,
    )

    assert simulation.additional_delay_minutes == 30

    print("✓ Flight simulation schema validated")

    try:

        FlightCreate(
            flight_number="AI305",
            airline="Air India",
            origin_code="HYD",
            destination_code="DEL",
            scheduled_departure=now + timedelta(hours=4),
            scheduled_arrival=now + timedelta(hours=2),
        )

        raise AssertionError(
            "Invalid flight schedule was accepted"
        )

    except ValidationError:

        print("✓ Invalid flight schedule rejected")

    print("\nAll Flight Operations schema tests passed.")


if __name__ == "__main__":
    test_flight_schemas()