import math

from datetime import datetime, timezone
from typing import TypedDict, NotRequired

from langgraph.graph import StateGraph, START, END

from app.agents.planning_agent import run_planning_agent, generate_fallback_plan

from app.rule_engine.engine import evaluate_operational_rules
from app.rule_engine.schemas import (
    OperationalInput,
    GateAssignmentInput,
)
from app.database.connection import get_db_connection

from app.tools.gate_availability_tool import (
    GateAvailabilityRequest,
    check_gate_availability,
    find_alternative_gates,
)

from app.database.flight_database import get_all_flights
from app.database.runway_database import get_runway_status

from app.tools.weather_data_tool import get_weather_data
from app.research_agent.agent import run_research_agent
from app.research_agent.config import settings as research_settings
from app.research_agent.schemas import (
    DataMode, DisruptionType, ResearchRequest,
)
from uuid import uuid4


# =========================================================
# WORKFLOW STATE
# =========================================================

class AirportWorkflowState(TypedDict):
    workflow_id: str
    airport: str
    disruption: str
    affected_flights: list[str]

    planning_result: NotRequired[dict]
    research_result: NotRequired[dict]

    gate_request: NotRequired[dict]
    gate_result: NotRequired[dict]
    permission_request_id: NotRequired[str]
    requested_by: NotRequired[str]
    staff_availability_checks: NotRequired[list[dict]]

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
        "research_result": state.get("research_result"),
        "advisory_only": True,
    }

    research_status = (state.get("research_result") or {}).get("status")
    degraded = research_status != "success"
    mode = DataMode(research_settings.DATA_MODE)
    # Use a deterministic investigation-only plan when evidence is incomplete
    # or when live provider data must not be forwarded to an external LLM.
    planner = generate_fallback_plan if degraded or mode == DataMode.live else run_planning_agent
    result = planner(
        workflow_id=state["workflow_id"],
        airport=state["airport"],
        disruption=state["disruption"],
        affected_flights=state["affected_flights"],
        gate_information=state.get("gate_result") or {},
        operational_information=operational_information,
    )
    if degraded:
        status = "planning_degraded_research_pending_review"
    elif planner is generate_fallback_plan or result.status == "fallback_planning_used_pending_review":
        status = "fallback_planning_used_pending_review"
    else:
        status = "planning_gates_and_rules_completed_pending_review"
    return {"planning_result": result.model_dump(), "status": status}


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


def get_overlapping_gate_assignments(
    request: GateAvailabilityRequest,
) -> list[GateAssignmentInput]:
    """
    Retrieve existing SQLite gate assignments that overlap
    with the requested flight's gate and time interval.
    """

    connection = get_db_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                airport_code,
                flight_number,
                gate_id,
                start_minute,
                end_minute
            FROM gate_assignments
            WHERE airport_code = ?
              AND gate_id = ?
              AND start_minute < ?
              AND end_minute > ?
              AND flight_number != ?
            """,
            (
                request.airport_code,
                request.gate_id,
                request.end_minute,
                request.start_minute,
                request.flight_number,
            ),
        ).fetchall()

        return [
            GateAssignmentInput.model_validate(dict(row))
            for row in rows
        ]

    finally:
        connection.close()


# =========================================================
# RULE ENGINE
# =========================================================

def synthetic_delay_evidence(state, flight_number):
    """Use only structured, attributed synthetic evidence for this workflow."""
    result = state.get("research_result") or {}
    if (result.get("data_mode") != "synthetic"
        or result.get("workflow_id") != state["workflow_id"]
        or result.get("airport_code") != state["airport"].strip().upper()
        or result.get("status") not in ("success", "partial_success")):
        return None, "UNAVAILABLE_SYNTHETIC_EVIDENCE"
    matches = [f for f in result.get("flights", [])
               if f.get("requested_identifier", "").strip().upper() == flight_number]
    if len(matches) != 1 or matches[0].get("status") != "found":
        return None, "UNAVAILABLE_SYNTHETIC_EVIDENCE"
    f = matches[0]
    op = f.get("operational_data") or {}
    if op.get("flight_number") != flight_number:
        return None, "UNAVAILABLE_SYNTHETIC_EVIDENCE"
    airport = state["airport"].strip().upper()
    sources = {v.get("source_id"): v for v in result.get("sources", [])}
    values = []
    for endpoint, field in (("destination_airport", "arrival_delay_minutes"),
                            ("origin_airport", "departure_delay_minutes")):
        if op.get(endpoint) != airport:
            continue
        value = op.get(field)
        if type(value) is not int or value < 0:
            continue
        if any(c.get("field_name") in (field, "operational_data." + field) and not c.get("resolved")
               for c in f.get("conflicts", [])):
            continue
        provenance = (f.get("field_sources") or {}).get("operational_data." + field) or {}
        source = sources.get(provenance.get("source_id")) or {}
        if (provenance.get("provider", "").lower() == "cirium-synthetic"
            and source.get("provider", "").lower() == "cirium-synthetic"
            and source.get("data_type", "").lower() == "synthetic"):
            values.append((value, "SYNTHETIC_CIRIUM:" + field + ":" + source["source_id"]))
    return max(values, key=lambda pair: pair[0]) if values else (None, "UNAVAILABLE_SYNTHETIC_EVIDENCE")


def live_delay_evidence(state, flight_number):
    """Use only structured, attributed live evidence for this workflow."""
    result = state.get("research_result") or {}
    if (result.get("data_mode") != "live"
        or result.get("workflow_id") != state["workflow_id"]
        or result.get("airport_code") != state["airport"].strip().upper()
        or result.get("status") not in ("success", "partial_success")):
        return None, "UNAVAILABLE_LIVE_EVIDENCE"
    matches = [f for f in result.get("flights", [])
               if f.get("requested_identifier", "").strip().upper() == flight_number]
    if len(matches) != 1 or matches[0].get("status") != "found":
        return None, "UNAVAILABLE_LIVE_EVIDENCE"
    f = matches[0]
    if f.get("conflicts") or result.get("errors") or f.get("provider") != "cirium":
        return None, "UNAVAILABLE_LIVE_EVIDENCE"
    op = f.get("operational_data") or {}
    if op.get("flight_number") != flight_number:
        return None, "UNAVAILABLE_LIVE_EVIDENCE"
    airport = state["airport"].strip().upper()
    sources = {v.get("source_id"): v for v in result.get("sources", [])}
    values = []
    for endpoint, field in (("destination_airport", "arrival_delay_minutes"),
                            ("origin_airport", "departure_delay_minutes")):
        if op.get(endpoint) != airport:
            continue
        value = op.get(field)
        if type(value) is not int or value < 0:
            continue
        if any(c.get("field_name") in (field, "operational_data." + field) and not c.get("resolved")
               for c in f.get("conflicts", [])):
            continue
        provenance = (f.get("field_sources") or {}).get("operational_data." + field) or {}
        source = sources.get(provenance.get("source_id")) or {}
        if (provenance.get("provider", "").lower() == "cirium"
            and source.get("provider", "").lower() == "cirium"
            and source.get("data_type", "").lower() == "live"):
            try:
                retrieved = datetime.fromisoformat(source["retrieved_at"].replace("Z", "+00:00"))
                if not 0 <= (datetime.now(timezone.utc) - retrieved).total_seconds() <= 300:
                    continue
            except (KeyError, TypeError, ValueError, AttributeError):
                continue
            values.append((value, "LIVE_CIRIUM:" + field + ":" + source["source_id"]))
    return max(values, key=lambda pair: pair[0]) if values else (None, "UNAVAILABLE_LIVE_EVIDENCE")


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

    # Do not call the live weather tool during synthetic execution.
    mode = DataMode(research_settings.DATA_MODE)
    if mode == DataMode.synthetic:
        weather = {"source": "SYNTHETIC_MODE_NO_RAINFALL_MEASUREMENT"}
        rainfall_mm = None
        observation_time = None
        observation_age_minutes = None
    else:
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
    if runway_available is True and not runway_info.get("verified"):
        runway_available = None

    # -----------------------------------------------------
    # 5. EVALUATE RULES FOR EACH FLIGHT
    # -----------------------------------------------------

    rule_results = []

    for flight_number in state["affected_flights"]:
        normalized_number = flight_number.strip().upper()
        matches = flight_lookup.get(normalized_number, [])

        if mode == DataMode.live and len(matches) > 1:
            raise ValueError(
                f"Multiple database records found for flight {flight_number}."
            )

        # Determine delay information from SQLite when available.
        if mode == DataMode.synthetic:
            delay_minutes, delay_source = synthetic_delay_evidence(state, normalized_number)
        else:
            delay_minutes, delay_source = live_delay_evidence(state, normalized_number)

        # -------------------------------------------------
        # 5A. RETRIEVE GATE ASSIGNMENT EVIDENCE
        # -------------------------------------------------

        gate_assignment = None
        existing_gate_assignments = None

        gate_data = state.get("gate_request")

        if gate_data:
            gate_request = GateAvailabilityRequest.model_validate(
                gate_data
            )

            if (
                gate_request.flight_number.strip().upper()
                == normalized_number
            ):
                gate_assignment = GateAssignmentInput(
                    airport_code=gate_request.airport_code,
                    flight_number=gate_request.flight_number,
                    gate_id=gate_request.gate_id,
                    start_minute=gate_request.start_minute,
                    end_minute=gate_request.end_minute,
                )

                existing_gate_assignments = (
                    get_overlapping_gate_assignments(gate_request)
                )

        # -------------------------------------------------
        # 5B. BUILD OPERATIONAL INPUT
        # -------------------------------------------------

        operational_input = OperationalInput(
            airport_code=airport,
            flight_number=normalized_number,
            delay_minutes=delay_minutes,
            rainfall_mm=rainfall_mm,
            runway_available=runway_available,
            gate_assignment=gate_assignment,
            existing_gate_assignments=existing_gate_assignments,
            staff_availability_checks=state.get(
                "staff_availability_checks"
            ),
            permission_request_id=state.get("permission_request_id"),
            requested_by=state.get("requested_by"),
        )

        result = evaluate_operational_rules(operational_input)

        rule_results.append({
            **result.model_dump(),
            "operational_inputs": {
                "delay_minutes": delay_minutes,
                "rainfall_mm": rainfall_mm,
                "runway_available": runway_available,
                "gate_assignment": (
                    gate_assignment.model_dump()
                    if gate_assignment else None
                ),
                "existing_gate_assignments": (
                    [
                        assignment.model_dump()
                        for assignment in existing_gate_assignments
                    ]
                    if existing_gate_assignments is not None
                    else None
                ),
            },
            "input_sources": {
                "delay_minutes": delay_source,
                "rainfall_mm": ("OPEN_METEO" if mode == DataMode.live else "UNAVAILABLE_SYNTHETIC_MODE"),
                "runway_available": runway_info["source"],
            },
            "weather_metadata": {
                "source": weather.get("source"),
                "observation_time": observation_time,
                "retrieved_at": weather.get("retrieved_at"),
                "cached": weather.get("cached", False),
                "observation_age_minutes": (round(observation_age_minutes, 2) if observation_age_minutes is not None else None),
            },
            "runway_metadata": runway_info,
            "advisory_only": True,
        })


    return {
        "rule_results": rule_results,
        "status": (
            "planning_gates_and_rules_completed_pending_review"
        ),
    }


# =========================================================
# RESEARCH AGENT
# =========================================================

def _classify_disruption(value: str) -> DisruptionType:
    text = value.lower()
    if any(word in text for word in ("weather", "rain", "wind", "storm", "fog", "visibility")):
        return DisruptionType.weather
    if any(word in text for word in ("delay", "late", "schedule")):
        return DisruptionType.delay
    if any(word in text for word in ("runway", "closure", "surface")):
        return DisruptionType.runway
    return DisruptionType.other


def research_agent_node(state: AirportWorkflowState) -> dict:
    """Collect weather/flight evidence before the Planning Agent reasons."""
    request = ResearchRequest(
        request_id=str(uuid4()),
        workflow_id=state["workflow_id"],
        airport_code=state["airport"],
        disruption_type=_classify_disruption(state["disruption"]),
        disruption_description=state["disruption"],
        affected_flights=state["affected_flights"],
        research_requirements=[
            "current weather conditions, wind, visibility and precipitation",
            "current aircraft position for affected flights",
            "aircraft altitude and velocity",
            "aircraft heading and ground status",
        ],
        planning_objective="Gather evidence to support the airport disruption planning workflow.",
        as_of=datetime.now(timezone.utc),
        data_mode=DataMode(research_settings.DATA_MODE),
    )
    result = run_research_agent(request)
    return {
        "research_result": result.model_dump(mode="json"),
        "status": "research_completed_" + result.status.value,
    }


# =========================================================
# BUILD LANGGRAPH WORKFLOW
# =========================================================

def build_airport_workflow():

    graph = StateGraph(AirportWorkflowState)

    graph.add_node(
        "research_agent",
        research_agent_node,
    )

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
        "research_agent",
    )

    graph.add_edge(
        "research_agent",
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