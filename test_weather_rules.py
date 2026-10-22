from pydantic import ValidationError

from app.rule_engine.weather_rules import (
    WeatherConditions,
    evaluate_weather_risk,
)


def main():

    print("\n=== WEATHER RULE ENGINE TESTS ===")

    # ----------------------------------------------
    # Test 1: Normal weather
    # ----------------------------------------------

    normal_weather = WeatherConditions(
        airport_code="HYD",
        flight_number="AI501",
        rainfall_mm=2.0,
        visibility_m=8000.0,
        wind_speed_kmh=15.0
    )

    result = evaluate_weather_risk(normal_weather)

    assert result.risk_level == "LOW"
    assert result.triggered_rules == 0
    assert result.advisory_only is True

    print("Test 1 passed: Normal weather produces LOW risk.")

    # ----------------------------------------------
    # Test 2: Rainfall threshold
    # ----------------------------------------------

    rainfall_weather = WeatherConditions(
        airport_code="HYD",
        flight_number="AI502",
        rainfall_mm=10.0,
        visibility_m=8000.0,
        wind_speed_kmh=15.0
    )

    result = evaluate_weather_risk(rainfall_weather)

    assert result.risk_level == "MEDIUM"
    assert result.triggered_rules == 1

    print("Test 2 passed: Rainfall threshold is detected.")

    # ----------------------------------------------
    # Test 3: Low visibility
    # ----------------------------------------------

    visibility_weather = WeatherConditions(
        airport_code="HYD",
        flight_number="AI503",
        rainfall_mm=0.0,
        visibility_m=500.0,
        wind_speed_kmh=10.0
    )

    result = evaluate_weather_risk(visibility_weather)

    assert result.risk_level == "MEDIUM"
    assert result.triggered_rules == 1

    print("Test 3 passed: Low visibility is detected.")

    # ----------------------------------------------
    # Test 4: High wind
    # ----------------------------------------------

    wind_weather = WeatherConditions(
        airport_code="HYD",
        flight_number="AI504",
        rainfall_mm=0.0,
        visibility_m=8000.0,
        wind_speed_kmh=45.0
    )

    result = evaluate_weather_risk(wind_weather)

    assert result.risk_level == "MEDIUM"
    assert result.triggered_rules == 1

    print("Test 4 passed: High wind is detected.")

    # ----------------------------------------------
    # Test 5: Multiple weather thresholds
    # ----------------------------------------------

    severe_weather = WeatherConditions(
        airport_code="HYD",
        flight_number="AI505",
        rainfall_mm=15.0,
        visibility_m=500.0,
        wind_speed_kmh=50.0
    )

    result = evaluate_weather_risk(severe_weather)

    assert result.risk_level == "HIGH"
    assert result.triggered_rules == 3
    assert len(result.messages) == 3

    print("Test 5 passed: Multiple weather risks are detected.")

    # ----------------------------------------------
    # Test 6: Invalid negative rainfall
    # ----------------------------------------------

    try:

        WeatherConditions(
            airport_code="HYD",
            flight_number="AI506",
            rainfall_mm=-5.0,
            visibility_m=8000.0,
            wind_speed_kmh=10.0
        )

        raise AssertionError(
            "Negative rainfall should be rejected."
        )

    except ValidationError:

        print(
            "Test 6 passed: Negative rainfall is rejected."
        )

    # ----------------------------------------------
    # Test 7: Boundary conditions
    # ----------------------------------------------

    boundary_weather = WeatherConditions(
        airport_code="HYD",
        flight_number="AI507",
        rainfall_mm=9.9,
        visibility_m=1000.0,
        wind_speed_kmh=39.9
    )

    result = evaluate_weather_risk(boundary_weather)

    assert result.risk_level == "LOW"
    assert result.triggered_rules == 0

    print(
        "Test 7 passed: Values below the configured "
        "thresholds do not trigger rules."
    )

    print("\nAll weather rule tests passed.")


if __name__ == "__main__":
    main()