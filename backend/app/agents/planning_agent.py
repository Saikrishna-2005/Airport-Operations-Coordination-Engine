import json
import logging

from app.agents.llm import get_llm
from app.agents.prompts import PLANNING_AGENT_PROMPT
from app.agents.schemas import PlanningResult


logger = logging.getLogger(__name__)


def is_temporary_llm_error(error: Exception) -> bool:
    """
    Identify temporary LLM service errors.
    """

    error_message = str(error).lower()

    temporary_error_codes = [
        "429",
        "500",
        "502",
        "503",
        "504",
        "resource_exhausted",
        "service_unavailable",
        "internal_server_error",
        "deadline_exceeded",
    ]

    return any(
        code in error_message
        for code in temporary_error_codes
    )


def generate_fallback_plan(
    workflow_id: str,
    airport: str,
    disruption: str,
    affected_flights: list[str],
    gate_information: dict,
    operational_information: dict,
) -> PlanningResult:
    """
    Generate a deterministic planning result when
    the Gemini service is temporarily unavailable.

    This fallback does not claim that live operational
    checks have been completed.
    """

    logger.warning(
        "Generating fallback planning result for workflow %s",
        workflow_id,
    )

    return PlanningResult(
        workflow_id=workflow_id,
        airport=airport,

        planning_objective=(
            f"Assess the reported disruption at {airport}, "
            f"identify its potential impact on affected flights, "
            "and prepare mitigation recommendations for "
            "human operational review."
        ),

        research_requirements=[
            (
                f"Verify the reported disruption: {disruption}."
            ),
            (
                "Verify the latest flight status and delay "
                "information for affected flights: "
                + ", ".join(affected_flights)
            ),
            (
                "Verify current airport weather information "
                "using an appropriate operational source."
            ),
            (
                "Confirm current runway status using "
                "an authorized airport information source."
            ),
        ],

        analysis_requirements=[
            (
                "Assess the potential impact of the disruption "
                "on affected flight operations."
            ),
            (
                "Review available rule engine results and "
                "identify triggered operational risks."
            ),
            (
                "Identify missing, incomplete, or unverified "
                "operational information."
            ),
            (
                "Evaluate whether further human review "
                "is required before proposing actions."
            ),
        ],

        resource_requirements=[
            (
                "Verify gate availability and possible "
                "gate conflicts."
            ),
            (
                "Verify staff availability, shift coverage, "
                "and existing assignments."
            ),
            (
                "Verify runway availability and relevant "
                "operational restrictions."
            ),
            (
                "Confirm that required operational "
                "permissions have been reviewed."
            ),
        ],

        proposed_steps=[
            (
                "Collect and verify the latest operational "
                "information for the affected airport."
            ),
            (
                "Review the flight, weather, runway, gate, "
                "staff, and permission information."
            ),
            (
                "Evaluate the existing rule engine results "
                "and identify unresolved risks."
            ),
            (
                "Prepare appropriate mitigation proposals "
                "for authorized personnel to review."
            ),
            (
                "Obtain the required human approval before "
                "considering any operational action."
            ),
        ],

        status="fallback_planning_used_pending_review",
    )


def run_planning_agent(
    workflow_id: str,
    airport: str,
    disruption: str,
    affected_flights: list[str],
    gate_information: dict | None = None,
    operational_information: dict | None = None,
) -> PlanningResult:

    # ---------------------------------
    # INPUT VALIDATION
    # ---------------------------------

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

    # ---------------------------------
    # OPERATIONAL INFORMATION
    # ---------------------------------

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

    # ---------------------------------
    # PRIMARY: GEMINI PLANNING
    # ---------------------------------

    try:

        logger.info(
            "Starting Gemini planning for workflow %s",
            workflow_id,
        )

        llm = get_llm()

        structured_llm = llm.with_structured_output(
            PlanningResult,
            method="function_calling",
        )

        planning_chain = (
            PLANNING_AGENT_PROMPT | structured_llm
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

        logger.info(
            "Gemini planning completed successfully "
            "for workflow %s",
            workflow_id,
        )

        return result

    # ---------------------------------
    # FALLBACK FOR TEMPORARY LLM ERRORS
    # ---------------------------------

    except Exception as error:

        if not is_temporary_llm_error(error):

            logger.exception(
                "Planning Agent failed due to a "
                "non-temporary error."
            )

            raise

        logger.warning(
            "Gemini temporarily unavailable for workflow %s. "
            "Using deterministic fallback. Error: %s",
            workflow_id,
            error,
        )

        return generate_fallback_plan(
            workflow_id=workflow_id,
            airport=airport,
            disruption=disruption,
            affected_flights=affected_flights,
            gate_information=gate_data,
            operational_information=operational_data,
        )