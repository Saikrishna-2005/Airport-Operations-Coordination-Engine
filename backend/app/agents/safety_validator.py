from dataclasses import dataclass, field

from app.agents.action_schemas import ActionProposal


ALLOWED_ACTIONS = {
    "request_gate_reallocation": {
        "current_gate",
        "requested_gate",
        "reason",
    },
    "request_staff_reallocation": {
        "staff_role",
        "quantity",
        "shift",
        "reason",
    },
    "notify_operations_team": {
        "team",
        "message",
    },
    "recommend_flight_review": {
        "reason",
        "risk_level",
    },
}


@dataclass
class ValidationResult:
    is_valid: bool
    status: str
    errors: list[str] = field(default_factory=list)


def validate_action(
    action: ActionProposal,
) -> ValidationResult:

    errors = []

    # 1. Validate action type
    if action.action_type not in ALLOWED_ACTIONS:
        errors.append("Unsupported action type.")

        return ValidationResult(
            is_valid=False,
            status="failed",
            errors=errors,
        )

    # 2. Validate description
    if not action.description.strip():
        errors.append("Action description cannot be empty.")

    # 3. Validate target flight
    if action.target_flight is not None:
        if not action.target_flight.strip():
            errors.append("Target flight cannot be blank.")

    if (
        action.action_type == "recommend_flight_review"
        and not action.target_flight
    ):
        errors.append(
            "A target flight is required for flight review."
        )

    # 4. Validate required and unexpected payload fields
    required_fields = ALLOWED_ACTIONS[action.action_type]

    missing_fields = (
        required_fields - set(action.payload.keys())
    )

    unexpected_fields = (
        set(action.payload.keys()) - required_fields
    )

    if missing_fields:
        errors.append(
            "Missing required payload fields: "
            + ", ".join(sorted(missing_fields))
        )

    if unexpected_fields:
        errors.append(
            "Unsupported payload fields: "
            + ", ".join(sorted(unexpected_fields))
        )

    # 5. Validate payload values
    for key, value in action.payload.items():

        if value is None:
            errors.append(
                f"Payload field '{key}' cannot be null."
            )

        elif isinstance(value, str) and not value.strip():
            errors.append(
                f"Payload field '{key}' cannot be empty."
            )

        elif isinstance(value, (dict, list)):
            errors.append(
                f"Payload field '{key}' must be a simple value."
            )

    # 6. Validate staff quantity
    if action.action_type == "request_staff_reallocation":

        quantity = action.payload.get("quantity")

        if (
            isinstance(quantity, bool)
            or not isinstance(quantity, int)
            or quantity <= 0
        ):
            errors.append(
                "Staff quantity must be a positive integer."
            )

    # 7. Validate risk level
    if action.action_type == "recommend_flight_review":

        risk_level = action.payload.get("risk_level")

        if risk_level not in {"low", "medium", "high"}:
            errors.append(
                "Risk level must be low, medium, or high."
            )

    # 8. Return validation result
    if errors:
        return ValidationResult(
            is_valid=False,
            status="failed",
            errors=errors,
        )

    return ValidationResult(
        is_valid=True,
        status="validated",
        errors=[],
    )