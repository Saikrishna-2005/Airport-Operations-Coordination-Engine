import pytest

from app.rule_engine.schemas import OperationalInput
from app.rule_engine.engine import evaluate_operational_rules


@pytest.mark.parametrize(
    "status, expected_triggered, expected_evaluation",
    [
        (True, False, "EVALUATED"),
        (False, True, "EVALUATED"),
        (None, False, "NOT_EVALUATED"),
    ],
)
def test_runway_status(status, expected_triggered, expected_evaluation):

    data = OperationalInput(
        airport_code="HYD",
        flight_number="TEST-FLT-001",
        delay_minutes=45,
        rainfall_mm=0.0,
        runway_available=status,
    )

    response = evaluate_operational_rules(data)

    runway_result = next(
        result
        for result in response.results
        if result.rule_id == "RULE-003"
    )

    assert runway_result.triggered is expected_triggered
    assert runway_result.evaluation_status == expected_evaluation