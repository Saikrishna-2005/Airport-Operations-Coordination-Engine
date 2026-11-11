from typing import Literal

from pydantic import BaseModel, Field


class ActionProposal(BaseModel):
    action_type: Literal[
        "request_gate_reallocation",
        "request_staff_reallocation",
        "notify_operations_team",
        "recommend_flight_review",
    ]

    description: str = Field(
        min_length=10,
        max_length=500,
    )

    target_flight: str | None = Field(
        default=None,
        max_length=20,
    )

    payload: dict = Field(
        default_factory=dict,
    )


class ActionProposalCreate(BaseModel):
    workflow_id: str
    airport: str = Field(
        min_length=3,
        max_length=4,
    )

    actions: list[ActionProposal] = Field(
        min_length=1,
        max_length=20,
    )


class ActionProposalResponse(BaseModel):
    action_id: str
    workflow_id: str
    airport: str
    action_type: str
    description: str
    target_flight: str | None
    validation_status: str
    approval_status: str
    execution_status: str


class ActionReviewRequest(BaseModel):
    decision: Literal["approved", "rejected"]

    review_comment: str = Field(
        min_length=3,
        max_length=500,
    )