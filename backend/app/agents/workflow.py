from typing import TypedDict, NotRequired

from langgraph.graph import StateGraph, START, END

from app.agents.planning_agent import run_planning_agent
from app.rule_engine.engine import evaluate_operational_rules
from app.rule_engine.schemas import OperationalInput

from app.tools.gate_availability_tool import (
    GateAvailabilityRequest,
    check_gate_availability,
    find_alternative_gates,
)


class AirportWorkflowState(TypedDict):
    workflow_id: str
    airport: str
    disruption: str
    affected_flights: list[str]

    planning_result: NotRequired[dict]
    gate_request: NotRequired[dict]
    gate_result: NotRequired[dict]
    rule_results: NotRequired[list[dict]]
    status: NotRequired[str]


def planning_node(state: AirportWorkflowState) -> dict:
    """Execute Gemini Planning Agent using verified gate information."""

    result = run_planning_agent(
        workflow_id=state["workflow_id"],
        airport=state["airport"],
        disruption=state["disruption"],
        affected_flights=state["affected_flights"],
        gate_information=state.get("gate_result"),
    )

    return {
        "planning_result": result.model_dump(),
        "status": "planning_completed_pending_review",
    }


def gate_availability_node(state: AirportWorkflowState) -> dict:
    """Check gate availability using existing SQLite assignments."""

    gate_data = state.get("gate_request")

    if not gate_data:
        return {
            "gate_result": {
                "status": "skipped",
                "reason": "No gate availability request provided",
            }
        }

    request = GateAvailabilityRequest.model_validate(gate_data)

    if request.airport_code.upper() != state["airport"].upper():
        raise ValueError(
            "Gate request airport does not match workflow airport"
        )

    if request.flight_number not in state["affected_flights"]:
        raise ValueError(
            "Gate request flight is not in affected flights"
        )

    result = check_gate_availability(request)

    if not result.available:
        result.alternative_gates = find_alternative_gates(
            request,
            ["G1", "G2", "G3"],
        )

    return {
        "gate_result": result.model_dump(),
        "status": "gate_availability_checked",
    }


def rule_engine_node(state: AirportWorkflowState) -> dict:
    """Evaluate operational rules for affected flights."""

    airport = state["airport"].strip().upper()
    disruption = state["disruption"].lower()

    rule_results = []

    for flight in state["affected_flights"]:
        operational_input = OperationalInput(
            airport_code=airport,
            flight_number=flight,
            delay_minutes=0,
            rainfall_mm=10.0 if "rain" in disruption else 0.0,
            runway_available=True,
        )

        result = evaluate_operational_rules(operational_input)

        rule_results.append(result.model_dump())

    return {
        "rule_results": rule_results,
        "status": "planning_gates_and_rules_completed_pending_review",
    }


def build_airport_workflow():
    graph = StateGraph(AirportWorkflowState)

    graph.add_node("planning_agent", planning_node)
    graph.add_node("gate_availability", gate_availability_node)
    graph.add_node("rule_engine", rule_engine_node)

    graph.add_edge(START, "gate_availability")
    graph.add_edge("gate_availability", "planning_agent")
    graph.add_edge("planning_agent", "rule_engine")
    graph.add_edge("rule_engine", END)

    return graph.compile()