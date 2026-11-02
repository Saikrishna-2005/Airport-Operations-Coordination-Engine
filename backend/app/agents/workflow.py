import math

from datetime import datetime, timezone
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

from app.database.flight_database import get_all_flights
from app.database.runway_database import get_runway_status

from app.tools.weather_data_tool import get_weather_data


# =========================================================
# WORKFLOW STATE
# =========================================================

class AirportWorkflowState(TypedDict):
    workflow_id: str
    airport: str
    disruption: str
    affected_flights: list[str]

    planning_result: NotRequired[dict]

    gate_request: NotRequired[dict]
    gate_result: NotRequired[dict]

    runway_code: NotRequired[str | None]

    rule_results: NotRequired[list[dict]]

    status: NotRequired[str]


# =========================================================
# PLANNING AGENT
# =========================================================

def planning_node(state: AirportWorkflowState) -> dict:
    """Generate a Gemini investigation plan from evaluated operational data."""

    operational_information = {
        "rule_results": state.get("rule_results", []),
        "advisory_only": True,
    }

    result = run_planning_agent(
        workflow_id=state["workflow_id"],
        airport=state["airport"],
        disruption=state["disruption"],
        affected_flights=state["affected_flights"],
        gate_information=state.get("gate_result"),
        operational_information=operational_information,
    )

    return {
        "planning_result": result.model_dump(),
        "status": "planning_gates_and_rules_completed_pending_review",
    }


# =========================================================
# GATE AVAILABILITY
# =========================================================

def gate_availability_node(
    state: AirportWorkflowState,
) -> dict:
    """
    Check gate availability using existing SQLite assignments.
    """

    gate_data = state.get("gate_request")

    if not gate_data:
        return {
            "gate_result": {
                "status": "skipped",
                "reason": "No gate availability request provided",
            }
        }

    request = GateAvailabilityRequest.model_validate(
        gate_data
    )

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


# =========================================================
# RUNWAY AVAILABILITY LOOKUP
# =========================================================

def resolve_runway_availability(
    airport_code: str,
    runway_code: str | None,
) -> dict:
    """
    Retrieve runway status from SQLite.

    Reports older than 30 minutes are treated as stale.

    Manual reports are advisory and unverified.
    """

    if not runway_code:
        return {
            "status": "UNKNOWN",
            "available": None,
            "reason": "No runway specified.",
            "source": "NO_RUNWAY_SELECTED",
            "verified": False,
        }

    airport_code = airport_code.strip().upper()
    runway_code = runway_code.strip().upper()

    runway = get_runway_status(
        airport_code=airport_code,
        runway_code=runway_code,
    )

    status = runway.get("status", "UNKNOWN")
    updated_at = runway.get("updated_at")

    if status == "UNKNOWN" or not updated_at:
        return {
            "status": "UNKNOWN",
            "available": None,
            "reason": runway.get(
                "reason",
                "No recorded runway status.",
            ),
            "source": "NO_CONFIRMED_STATUS",
            "verified": False,
            "runway_code": runway_code,
        }

    try:
        timestamp = datetime.fromisoformat(
            updated_at.replace("Z", "+00:00")
        )

        if timestamp.tzinfo is None:
            raise ValueError(
                "Runway timestamp has no timezone."
            )

        timestamp = timestamp.astimezone(timezone.utc)

        age_minutes = (
            datetime.now(timezone.utc) - timestamp
        ).total_seconds() / 60

    except (ValueError, TypeError, AttributeError):
        return {
            "status": "UNKNOWN",
            "available": None,
            "reason": "Invalid runway status timestamp.",
            "source": "INVALID_TIMESTAMP",
            "verified": False,
            "runway_code": runway_code,
        }

    # Development freshness threshold.
    # Not an aviation-certified operational standard.

    if age_minutes < -5 or age_minutes > 30:
        return {
            "status": "UNKNOWN",
            "available": None,
            "reason": (
                "Runway status report is stale or invalid."
            ),
            "source": "STALE_MANUAL_REPORT",
            "verified": False,
            "runway_code": runway_code,
            "age_minutes": round(age_minutes, 2),
        }

    if status not in ("AVAILABLE", "UNAVAILABLE"):
        return {
            "status": "UNKNOWN",
            "available": None,
            "reason": "Unsupported runway status.",
            "source": "INVALID_STATUS",
            "verified": False,
            "runway_code": runway_code,
        }

    return {
        "status": status,
        "available": status == "AVAILABLE",
        "reason": runway.get("reason"),
        "source": "MANUAL_USER_REPORT",
        "verified": False,
        "runway_code": runway_code,
        "updated_by": runway.get("updated_by"),
        "updated_at": updated_at,
        "age_minutes": round(age_minutes, 2),
    }


# =========================================================
# RULE ENGINE
# =========================================================

def rule_engine_node(
    state: AirportWorkflowState,
) -> dict:
    """
    Evaluate operational rules using:

    1. Flight delays from SQLite.
    2. Rainfall measurements from Open-Meteo.
    3. Reported runway availability from SQLite.

    Results are advisory only.
    """

    airport = state["airport"].strip().upper()

    # -----------------------------------------------------
    # 1. RETRIEVE FLIGHT DATA
    # -----------------------------------------------------

    database_flights = get_all_flights()

    flight_lookup = {}

    for flight in database_flights:
        number = flight["flight_number"].strip().upper()

        flight_lookup.setdefault(
            number,
            [],
        ).append(flight)

    # -----------------------------------------------------
    # 2. RETRIEVE WEATHER DATA
    # -----------------------------------------------------

    weather = get_weather_data(airport)

    if not weather.get("success"):
        raise ValueError(
            "Weather data unavailable: "
            + str(
                weather.get(
                    "reason",
                    "Unknown weather provider error",
                )
            )
        )

    rainfall_value = weather.get("rain_mm")

    if rainfall_value is None:
        raise ValueError(
            "Weather data unavailable: "
            "rain_mm measurement is missing."
        )

    try:
        rainfall_mm = float(rainfall_value)

    except (TypeError, ValueError):
        raise ValueError(
            "Weather data unavailable: "
            "rain_mm is not a valid numeric measurement."
        )

    if not math.isfinite(rainfall_mm) or rainfall_mm < 0:
        raise ValueError(
            "Weather data unavailable: "
            "rain_mm must be finite and non-negative."
        )

    # -----------------------------------------------------
    # 3. VALIDATE WEATHER OBSERVATION TIME
    # -----------------------------------------------------

    observation_time = weather.get("observation_time")

    if not observation_time:
        raise ValueError(
            "Weather observation time is missing."
        )

    try:
        observed_at = datetime.fromisoformat(
            observation_time.replace("Z", "+00:00")
        )

        # Open-Meteo is requested with timezone="UTC".
        # Its timestamps may omit an explicit UTC offset.

        if observed_at.tzinfo is None:
            observed_at = observed_at.replace(
                tzinfo=timezone.utc
            )
        else:
            observed_at = observed_at.astimezone(
                timezone.utc
            )

    except (TypeError, AttributeError, ValueError) as exc:
        raise ValueError(
            f"Invalid weather observation time: {exc}"
        )

    observation_age_minutes = (
        datetime.now(timezone.utc) - observed_at
    ).total_seconds() / 60

    # Configurable development freshness threshold.

    if not -5 <= observation_age_minutes <= 60:
        raise ValueError(
            "Weather observation is outside the "
            "configured 60-minute freshness window."
        )

    # -----------------------------------------------------
    # 4. RETRIEVE RUNWAY STATUS
    # -----------------------------------------------------

    runway_info = resolve_runway_availability(
        airport_code=airport,
        runway_code=state.get("runway_code"),
    )

    runway_available = runway_info["available"]

    # -----------------------------------------------------
    # 5. EVALUATE RULES FOR EACH FLIGHT
    # -----------------------------------------------------

    rule_results = []

    for flight_number in state["affected_flights"]:

        normalized_number = flight_number.strip().upper()

        matches = flight_lookup.get(
            normalized_number,
            [],
        )

        if not matches:
            raise ValueError(
                f"Flight {flight_number} was not found "
                "in the database."
            )

        if len(matches) > 1:
            raise ValueError(
                f"Multiple database records match "
                f"flight {flight_number}. "
                "Use a unique flight identifier."
            )

        flight_record = matches[0]

        delay_minutes = int(
            flight_record.get("delay_minutes") or 0
        )

        # -------------------------------------------------
        # 6. BUILD VALIDATED OPERATIONAL INPUT
        # -------------------------------------------------

        operational_input = OperationalInput(
            airport_code=airport,
            flight_number=normalized_number,
            delay_minutes=delay_minutes,
            rainfall_mm=rainfall_mm,
            runway_available=runway_available,
        )

        # -------------------------------------------------
        # 7. EXECUTE RULE ENGINE
        # -------------------------------------------------

        result = evaluate_operational_rules(
            operational_input
        )

        # -------------------------------------------------
        # 8. BUILD RESPONSE
        # -------------------------------------------------

        rule_results.append(
            {
                **result.model_dump(),

                "operational_inputs": {
                    "delay_minutes": delay_minutes,
                    "rainfall_mm": rainfall_mm,
                    "runway_available": runway_available,
                },

                "input_sources": {
                    "delay_minutes": "SQLITE_FLIGHT_DATABASE",
                    "rainfall_mm": "OPEN_METEO",
                    "runway_available": runway_info["source"],
                },

                "weather_metadata": {
                    "source": weather.get("source"),
                    "observation_time": observation_time,
                    "retrieved_at": weather.get("retrieved_at"),
                    "cached": weather.get("cached", False),
                    "observation_age_minutes": round(
                        observation_age_minutes,
                        2,
                    ),
                },

                "runway_metadata": runway_info,

                "advisory_only": True,
            }
        )

    return {
        "rule_results": rule_results,
        "status": (
            "planning_gates_and_rules_completed_pending_review"
        ),
    }


# =========================================================
# BUILD LANGGRAPH WORKFLOW
# =========================================================

def build_airport_workflow():

    graph = StateGraph(AirportWorkflowState)

    graph.add_node(
        "planning_agent",
        planning_node,
    )

    graph.add_node(
        "gate_availability",
        gate_availability_node,
    )

    graph.add_node(
        "rule_engine",
        rule_engine_node,
    )

    graph.add_edge(
        START,
        "gate_availability",
    )

    graph.add_edge(
        "gate_availability",
        "rule_engine",
    )

    graph.add_edge(
        "rule_engine",
        "planning_agent",
    )

    graph.add_edge(
        "planning_agent",
        END,
    )

    return graph.compile()