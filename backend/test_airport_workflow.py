from app.agents.workflow import build_airport_workflow


def main():
    workflow = build_airport_workflow()

    initial_state = {
        "workflow_id": "WF-002",
        "airport": "HYD",
        "disruption": (
            "Heavy rainfall has been reported. "
            "Potential flight delays need investigation."
        ),
        "affected_flights": ["TEST-FLT-001", "TEST-FLT-002"],

        "gate_request": {
            "airport_code": "HYD",
            "flight_number": "TEST-FLT-001",
            "gate_id": "G1",
            "start_minute": 600,
            "end_minute": 660,
        },

        "planning_result": {},
        "status": "planning_started",
    }
    result = workflow.invoke(initial_state)

    print("\n--- AIRPORT OPERATIONS WORKFLOW RESULT ---")
    print(result["planning_result"])
    print("\nWorkflow status:", result["status"])


if __name__ == "__main__":
    main()