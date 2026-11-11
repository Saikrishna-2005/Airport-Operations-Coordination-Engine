from app.agents.action_schemas import ActionProposal
from app.agents.safety_validator import validate_action


action = ActionProposal(
    action_type="request_gate_reallocation",
    description="Recommend reviewing an alternative gate",
    target_flight="AI101",
    payload={
        "current_gate": "G12",
        "requested_gate": "G15",
        "reason": "Gate availability issue",
    },
)

result = validate_action(action)

print(result)