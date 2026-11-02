from app.rule_engine.schemas import OperationalInput
from app.rule_engine.engine import evaluate_operational_rules


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

    print("\nRunway input:", status)
    print("Triggered:", runway_result.triggered)
    print("Severity:", runway_result.severity)
    print("Evaluation status:", runway_result.evaluation_status)
    print("Message:", runway_result.message)


print("TEST 1: RUNWAY AVAILABLE")
test_runway_status(
    status=True,
    expected_triggered=False,
    expected_evaluation="EVALUATED",
)

print("\nTEST 2: RUNWAY UNAVAILABLE")
test_runway_status(
    status=False,
    expected_triggered=True,
    expected_evaluation="EVALUATED",
)

print("\nTEST 3: RUNWAY UNKNOWN")
test_runway_status(
    status=None,
    expected_triggered=False,
    expected_evaluation="NOT_EVALUATED",
)

print("\nALL RUNWAY RULE TESTS PASSED")