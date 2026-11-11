from app.agents.action_generator import generate_action_proposals


# Sample test evidence only — not real airport data.

planning_result = {
    "workflow_id": "TEST-WORKFLOW-001",
    "airport": "DEL",
    "planning_objective": "Investigate a reported flight delay.",
    "research_requirements": [
        "Verify flight information."
    ],
    "analysis_requirements": [
        "Investigate the reported 45-minute delay."
    ],
    "resource_requirements": [
        "Check operational requirements."
    ],
    "proposed_steps": [
        "Review the affected flight."
    ],
}

research_result = {
    "status": "success",
    "airport": "DEL",
    "data_mode": "live",
    "findings": [
        {
            "flight": "AI306",
            "status": "provider_fact",
            "delay_minutes": 45,
        }
    ],
    "missing_information": [],
}

rule_results = [
    {
        "rule_id": "RULE-001",
        "status": "TRIGGERED",
        "severity": "medium",
        "flight": "AI306",
        "delay_minutes": 45,
    }
]

result = generate_action_proposals(
    workflow_id="TEST-WORKFLOW-001",
    airport="DEL",
    planning_result=planning_result,
    research_result=research_result,
    rule_results=rule_results,
    gate_information={},
)

print("\n========== GENERATED ACTION PROPOSALS ==========")

for action in result.actions:
    print(action.model_dump_json(indent=2))

if not result.actions:
    print("No action proposals generated.")

print("\n========== SAFETY VALIDATION RESULTS ==========")

for validation in result.validation_results:
    print(validation)

print("\n========== TEST COMPLETED ==========")