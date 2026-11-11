from app.rule_engine.schemas import (
    OperationalInput,
    GateAssignmentInput,
)

from app.rule_engine.engine import evaluate_operational_rules


existing_assignment = GateAssignmentInput(
    airport_code="HYD",
    flight_number="AI501",
    gate_id="G1",
    start_minute=600,
    end_minute=660,
)


# TEST 1: Another flight requests the same gate
# with overlapping time: 10:30–11:30

conflict_input = OperationalInput(
    airport_code="HYD",
    flight_number="AI502",
    delay_minutes=None,
    rainfall_mm=None,
    runway_available=None,
    gate_assignment=GateAssignmentInput(
        airport_code="HYD",
        flight_number="AI502",
        gate_id="G1",
        start_minute=630,
        end_minute=690,
    ),
    existing_gate_assignments=[existing_assignment],
)


# TEST 2: Another flight requests the same gate
# without overlapping time: 11:30–12:30

no_conflict_input = OperationalInput(
    airport_code="HYD",
    flight_number="AI503",
    delay_minutes=None,
    rainfall_mm=None,
    runway_available=None,
    gate_assignment=GateAssignmentInput(
        airport_code="HYD",
        flight_number="AI503",
        gate_id="G1",
        start_minute=690,
        end_minute=750,
    ),
    existing_gate_assignments=[existing_assignment],
)


for test_name, test_input in [
    ("TEST 1 - Overlapping Gate Assignment", conflict_input),
    ("TEST 2 - Non-Overlapping Gate Assignment", no_conflict_input),
]:

    response = evaluate_operational_rules(test_input)

    print("\n", "=" * 55)
    print(test_name)
    print("=" * 55)

    for rule in response.results:
        if rule.rule_id == "RULE-004":
            print(rule.model_dump())
