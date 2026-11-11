from app.rule_engine.schemas import RuleResult
from app.rule_engine.decision_support import evaluate_decision_support


def create_results(triggered_rule=None, not_evaluated=None):

    results = []

    rules = [
        ("RULE-001", "Flight Delay Risk"),
        ("RULE-002", "Heavy Rainfall Risk"),
        ("RULE-003", "Runway Availability Risk"),
        ("RULE-004", "Gate Conflict Detection"),
        ("RULE-007", "Staff Availability Validation"),
        ("RULE-008", "Operational Permission Validation"),
    ]

    for rule_id, rule_name in rules:

        is_triggered = rule_id == triggered_rule

        results.append(
            RuleResult(
                rule_id=rule_id,
                rule_name=rule_name,
                triggered=is_triggered,
                severity="HIGH" if is_triggered else "LOW",
                message=f"{rule_name} test result",
                evaluation_status=(
                    "NOT_EVALUATED"
                    if rule_id == not_evaluated
                    else "EVALUATED"
                ),
            )
        )

    return results


# TEST 1: All rules pass
print("\nTEST 1: GRANT")
result = evaluate_decision_support(create_results())
print(result.model_dump())


# TEST 2: Gate conflict
print("\nTEST 2: HOLD")
result = evaluate_decision_support(
    create_results(triggered_rule="RULE-004")
)
print(result.model_dump())


# TEST 3: Flight delay
print("\nTEST 3: DELAY")
result = evaluate_decision_support(
    create_results(triggered_rule="RULE-001")
)
print(result.model_dump())


# TEST 4: Missing evidence
print("\nTEST 4: MISSING DATA")
result = evaluate_decision_support(
    create_results(not_evaluated="RULE-003")
)
print(result.model_dump())