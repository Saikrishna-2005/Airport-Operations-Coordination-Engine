from app.rule_engine.schemas import (
    RuleResult,
    DecisionSupportResult,
)


# Rules that must be evaluated before recommending GRANT.
REQUIRED_RULES = {
    "RULE-001",
    "RULE-002",
    "RULE-003",
    "RULE-004",
    "RULE-007",
    "RULE-008",
}

# Operational risks that recommend DELAY.
DELAY_RULES = {
    "RULE-001",
    "RULE-002",
    "RULE-003",
}


def evaluate_decision_support(
    results: list[RuleResult],
) -> DecisionSupportResult:
    """
    Consolidate individual rule results into
    a GRANT, HOLD, or DELAY recommendation.

    This function is advisory only.
    """

    reasons = []

    if not results:
        return DecisionSupportResult(
            decision="HOLD",
            reasons=[
                "No rule evaluation results are available."
            ],
            evaluation_status="NOT_EVALUATED",
        )

    # Identify missing rule results.
    evaluated_rule_ids = {
        result.rule_id for result in results
    }

    missing_rules = REQUIRED_RULES - evaluated_rule_ids

    # Identify rules that could not be evaluated.
    not_evaluated_rules = [
        result.rule_id
        for result in results
        if result.evaluation_status == "NOT_EVALUATED"
    ]

    # Collect triggered rules.
    triggered_results = [
        result for result in results
        if result.triggered
    ]

    # DELAY has the highest priority.
    delay_results = [
        result for result in triggered_results
        if result.rule_id in DELAY_RULES
    ]

    if delay_results:
        for result in delay_results:
            reasons.append(
                f"{result.rule_id}: {result.message}"
            )

        return DecisionSupportResult(
            decision="DELAY",
            reasons=reasons,
        )

    # Other triggered rules recommend HOLD.
    if triggered_results:
        for result in triggered_results:
            reasons.append(
                f"{result.rule_id}: {result.message}"
            )

        return DecisionSupportResult(
            decision="HOLD",
            reasons=reasons,
        )

    # Missing or unavailable evidence prevents GRANT.
    if missing_rules or not_evaluated_rules:

        if missing_rules:
            reasons.append(
                "Missing rule results: "
                + ", ".join(sorted(missing_rules))
            )

        if not_evaluated_rules:
            reasons.append(
                "Some rules could not be evaluated: "
                + ", ".join(sorted(set(not_evaluated_rules)))
            )

        return DecisionSupportResult(
            decision="HOLD",
            reasons=reasons,
            evaluation_status="NOT_EVALUATED",
        )

    # All required rules were evaluated successfully.
    return DecisionSupportResult(
        decision="GRANT",
        reasons=[
            "All required configured rule checks were "
            "evaluated successfully with no triggered risks."
        ],
        evaluation_status="EVALUATED",
    )