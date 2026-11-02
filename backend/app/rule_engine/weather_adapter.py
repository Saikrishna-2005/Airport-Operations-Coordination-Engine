from app.rule_engine.weather_rules import (
    WeatherConditions,
    evaluate_weather_risk,
)


def evaluate_airport_weather(
    airport_code: str,
    rainfall_mm: float,
    visibility_m: float,
    wind_speed_kmh: float,
):
    """
    Evaluate airport-level weather using the existing
    flight-level weather rule engine.

    The flight number is a monitoring reference only.
    This function does not evaluate an actual flight.
    """

    conditions = WeatherConditions(
        airport_code=airport_code,
        flight_number="WX-MON",
        rainfall_mm=rainfall_mm,
        visibility_m=visibility_m,
        wind_speed_kmh=wind_speed_kmh,
    )

    result = evaluate_weather_risk(conditions)

    return {
        "airport_code": result.airport_code,
        "risk_level": result.risk_level,
        "triggered_rules": result.triggered_rules,
        "messages": result.messages,
        "advisory_only": result.advisory_only,
        "evaluation_scope": "AIRPORT",
    }