from app.agents.action_schemas import ActionProposal
from app.agents.safety_validator import validate_action


# Test 1: Valid notification
valid_action = ActionProposal(
    action_type="notify_operations_team",
    description="Notify airport operations about the disruption.",
    target_flight="AI306",
    payload={
        "team": "Airport Operations",
        "message": "Review flight AI306 operational status."
    }
)

result = validate_action(valid_action)

print("TEST 1 - Valid Action")
print(result)


# Test 2: Missing required payload
invalid_action = ActionProposal(
    action_type="notify_operations_team",
    description="Notify airport operations about the disruption.",
    target_flight="AI306",
    payload={
        "team": "Airport Operations"
    }
)

result = validate_action(invalid_action)

print("\nTEST 2 - Missing Payload")
print(result)


# Test 3: Invalid risk level
risk_action = ActionProposal(
    action_type="recommend_flight_review",
    description="Recommend reviewing flight AI306.",
    target_flight="AI306",
    payload={
        "reason": "Operational disruption",
        "risk_level": "critical"
    }
)

result = validate_action(risk_action)

print("\nTEST 3 - Invalid Risk Level")
print(result)