import json

from app.agents.llm import get_llm
from app.agents.prompts import PLANNING_AGENT_PROMPT
from app.agents.schemas import PlanningResult


def run_planning_agent(
    workflow_id: str,
    airport: str,
    disruption: str,
    affected_flights: list[str],
    gate_information: dict | None = None,
    operational_information: dict | None = None,
) -> PlanningResult:

    if not workflow_id.strip():
        raise ValueError("Workflow ID cannot be empty.")

    airport = airport.strip().upper()

    if not 3 <= len(airport) <= 4:
        raise ValueError(
            "Airport code must contain 3 or 4 characters."
        )

    if not disruption.strip():
        raise ValueError(
            "Disruption description cannot be empty."
        )

    if not affected_flights:
        raise ValueError(
            "At least one affected flight must be provided."
        )

    llm = get_llm()

    structured_llm = llm.with_structured_output(
        PlanningResult
    )

    planning_chain = (
        PLANNING_AGENT_PROMPT | structured_llm
    )

    gate_data = (
        gate_information
        if gate_information is not None
        else {
            "status": "not_checked",
            "reason": "No gate request was provided",
        }
    )

    operational_data = (
        operational_information
        if operational_information is not None
        else {
            "status": "not_available",
            "reason": (
                "Operational rule evaluation "
                "has not been provided."
            ),
        }
    )

    result = planning_chain.invoke(
        {
            "workflow_id": workflow_id,
            "airport": airport,
            "disruption": disruption,
            "affected_flights": ", ".join(
                affected_flights
            ),
            "gate_information": json.dumps(
                gate_data,
                indent=2,
            ),
            "operational_information": json.dumps(
                operational_data,
                indent=2,
            ),
        }
    )

    if not isinstance(result, PlanningResult):
        raise TypeError(
            "Planning Agent did not return "
            "a valid PlanningResult."
        )

    return result