import json

from pydantic import BaseModel, Field, field_validator

from app.agents.llm import get_llm
from app.agents.action_schemas import ActionProposal
from app.agents.action_prompts import ACTION_PROPOSAL_PROMPT
from app.agents.safety_validator import validate_action
from app.config import settings


class ActionProposalBatch(BaseModel):
    actions: list[ActionProposal] = Field(
        default_factory=list,
        max_length=20,
        description=(
            "Evidence-supported operational action proposals. "
            "Return an empty list if no action is justified."
        ),
    )

    validation_results: list[dict] = Field(
        default_factory=list
    )

    @field_validator("actions", mode="before")
    @classmethod
    def normalize_action_payloads(cls, actions):
        if not isinstance(actions, list):
            return actions

        normalized_actions = []

        for action in actions:
            if isinstance(action, dict):
                action = action.copy()

                payload = action.get("payload")

                if isinstance(payload, str):
                    action["payload"] = json.loads(payload)

            normalized_actions.append(action)

        return normalized_actions


def collect_evidence_gaps(evidence: dict) -> list[str]:
    """
    Identify missing or unavailable operational information
    from Research Agent, Planning Agent and Rule Engine results.
    """

    gap_keywords = (
        "not evaluated",
        "not available",
        "unavailable",
        "not found",
        "unknown",
        "missing",
        "not provided",
        "could not",
    )

    gaps = []

    def inspect(value):
        if isinstance(value, dict):
            for item in value.values():
                inspect(item)

        elif isinstance(value, list):
            for item in value:
                inspect(item)

        elif isinstance(value, str):
            text = " ".join(value.split())

            if any(keyword in text.lower() for keyword in gap_keywords):
                if text not in gaps:
                    gaps.append(text)

    inspect(evidence)

    return gaps[:8]


def validate_generated_actions(actions):
    """
    Validate every generated action using the existing Safety Validator.
    """

    validation_results = []

    for index, action in enumerate(actions):

        validation = validate_action(action)

        validation_results.append({
            "action_index": index,
            "action_type": action.action_type,
            "validation_status": validation.status,
            "is_valid": validation.is_valid,
            "errors": validation.errors,
        })

    return validation_results


def generate_action_proposals(
    workflow_id: str,
    airport: str,
    planning_result: dict,
    research_result: dict | None = None,
    rule_results: list | None = None,
    gate_information: dict | None = None,
) -> ActionProposalBatch:

    if not workflow_id.strip():
        raise ValueError("Workflow ID cannot be empty.")

    airport = airport.strip().upper()

    if not 3 <= len(airport) <= 4:
        raise ValueError("Airport code must contain 3 or 4 characters.")

    if not isinstance(planning_result, dict):
        raise ValueError("Planning result must be a dictionary.")

    if not planning_result:
        raise ValueError("Planning result cannot be empty.")

    # Collect operational evidence.
    operational_evidence = {
        "planning_result": planning_result,
        "research_result": research_result or {},
        "rule_results": rule_results or [],
        "gate_information": gate_information or {},
        "notification_configuration": {
            "default_team": settings.default_notification_team,
        },
    }

    # Identify important evidence gaps.
    evidence_gaps = collect_evidence_gaps(
        operational_evidence
    )

    # Generate proposals using the LLM.
    llm = get_llm()

    structured_llm = llm.with_structured_output(
        ActionProposalBatch,
        method="function_calling",
    )

    action_chain = ACTION_PROPOSAL_PROMPT | structured_llm

    result = action_chain.invoke(
        {
            "workflow_id": workflow_id,
            "airport": airport,
            "operational_evidence": json.dumps(
                operational_evidence,
                indent=2,
                default=str,
            ),
        }
    )

    if not isinstance(result, ActionProposalBatch):
        raise TypeError(
            "Action Proposal Generator returned an invalid result."
        )

    # Evidence-gap fallback.
    # This works even when the LLM returns zero proposals.
    if evidence_gaps:

        default_team = settings.default_notification_team

        already_has_notification = any(
            action.action_type == "notify_operations_team"
            for action in result.actions
        )

        if default_team and not already_has_notification:

            gap_message = (
                f"Operational information requires verification "
                f"for airport {airport}. "
                + "Evidence gaps: "
                + "; ".join(evidence_gaps)
            )

            notification = ActionProposal(
                action_type="notify_operations_team",
                description=(
                    f"Notify the operations team about important "
                    f"missing or unverified operational information "
                    f"for airport {airport}. "
                    f"Human verification is required."
                ),
                payload={
                    "team": default_team,
                    "message": gap_message,
                },
            )

            result.actions.append(notification)

    # Safety validation for all generated proposals.
    result.validation_results = validate_generated_actions(
        result.actions
    )

    return result