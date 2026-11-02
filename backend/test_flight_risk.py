from app.rule_engine.flight_risk import (
    calculate_flight_risk
)


def test_flight_risk():

    # TEST 1: Normal flight
    result = calculate_flight_risk(
        delay_minutes=0,
        status="SCHEDULED",
    )

    assert result["risk_score"] == 0
    assert result["risk_level"] == "LOW"

    print("✓ Normal flight risk calculated")

    # TEST 2: 30-minute delay
    result = calculate_flight_risk(
        delay_minutes=30,
        status="DELAYED",
    )

    assert result["risk_score"] == 40
    assert result["risk_level"] == "MEDIUM"

    print("✓ Medium flight risk calculated")

    # TEST 3: 75-minute delay
    result = calculate_flight_risk(
        delay_minutes=75,
        status="DELAYED",
    )

    assert result["risk_score"] == 55
    assert result["risk_level"] == "HIGH"

    print("✓ High flight risk calculated")

    # TEST 4: 150-minute delay
    result = calculate_flight_risk(
        delay_minutes=150,
        status="DELAYED",
    )

    assert result["risk_score"] == 70
    assert result["risk_level"] == "HIGH"

    print("✓ Extended delay risk calculated")

    # TEST 5: Cancelled flight
    result = calculate_flight_risk(
        delay_minutes=0,
        status="CANCELLED",
    )

    assert result["risk_score"] == 40

    print("✓ Cancelled flight risk calculated")

    # TEST 6: Risk factors
    result = calculate_flight_risk(
        delay_minutes=75,
        status="DELAYED",
    )

    assert len(result["risk_factors"]) == 2

    print("✓ Flight risk factors generated")

    print("\nAll Flight Risk Engine tests passed.")


if __name__ == "__main__":
    test_flight_risk()