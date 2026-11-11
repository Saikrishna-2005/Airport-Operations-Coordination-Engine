import logging

from app.rule_engine.schemas import (
    OperationalInput,
    RuleEvaluationResponse,
    RuleResult,
)

from app.rule_engine.rules import (
    evaluate_delay_rule,
    evaluate_rainfall_rule,
    evaluate_runway_rule,
    evaluate_gate_conflict_rule,
    evaluate_staff_availability_rule,
    evaluate_permission_validation_rule,
)

from app.rule_engine.decision_support import (
    evaluate_decision_support,
)


logger = logging.getLogger(__name__)


def evaluate_operational_rules(
    data: OperationalInput,
) -> RuleEvaluationResponse:
    """Evaluate airport operational data against predefined rules."""

    logger.info(
        "Starting rule evaluation for airport=%s, flight=%s",
        data.airport_code,
        data.flight_number,
    )

    rule_evaluators = [
        evaluate_delay_rule,
        evaluate_rainfall_rule,
        evaluate_runway_rule,
        evaluate_gate_conflict_rule,
        evaluate_staff_availability_rule,
        evaluate_permission_validation_rule,
    ]

    results: list[RuleResult] = [
        evaluator(data) for evaluator in rule_evaluators
    ]

    triggered_count = sum(
        1 for result in results if result.triggered
    )

    logger.info(
        "Rule evaluation completed for flight=%s; triggered_rules=%d",
        data.flight_number,
        triggered_count,
    )

    decision = evaluate_decision_support(results)

    return RuleEvaluationResponse(
        airport_code=data.airport_code,
        flight_number=data.flight_number,
        triggered_rules=triggered_count,
        results=results,
        decision_support=decision,
        advisory_only=True,
    )
