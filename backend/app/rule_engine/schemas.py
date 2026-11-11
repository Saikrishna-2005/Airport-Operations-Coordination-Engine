from typing import Literal

from pydantic import BaseModel, Field, model_validator


class GateAssignmentInput(BaseModel):
    """Gate assignment evidence used for conflict evaluation."""

    airport_code: str = Field(
        min_length=3,
        max_length=4,
    )

    flight_number: str = Field(
        min_length=2,
        max_length=20,
    )

    gate_id: str = Field(
        min_length=1,
    )

    start_minute: int = Field(
        ge=0,
        le=1439,
    )

    end_minute: int = Field(
        ge=1,
        le=1440,
    )

    @model_validator(mode="after")
    def validate_time_interval(self):
        if self.end_minute <= self.start_minute:
            raise ValueError(
                "end_minute must be greater than start_minute"
            )

        return self

class StaffAvailabilityInput(BaseModel):
    """Staff member and time window to validate."""

    staff_id: str = Field(min_length=1)

    requested_date: str

    start_time: str = Field(
        pattern=r"^([01]\d|2[0-3]):[0-5]\d$"
    )

    end_time: str = Field(
        pattern=r"^([01]\d|2[0-3]):[0-5]\d$"
    )

class OperationalInput(BaseModel):
    """Validated operational data supplied to the Rule Engine."""

    airport_code: str = Field(
        ...,
        min_length=3,
        max_length=4,
        description="Airport code, such as HYD",
    )

    flight_number: str = Field(
        ...,
        min_length=2,
        max_length=20,
        description="Flight identifier, such as AI501",
    )

    delay_minutes: int | None = Field(
        default=None,
        ge=0,
        description=(
            "Reported flight delay in minutes. "
            "None means delay information is unavailable."
        ),
    )

    rainfall_mm: float | None = Field(
        default=None,
        ge=0,
        description=(
            "Reported rainfall in millimetres. "
            "None means a separate rainfall measurement is unavailable."
        ),
    )

    runway_available: bool | None = Field(
        default=None,
        description=(
            "Reported runway availability. "
            "True=available, False=unavailable, "
            "None=unknown or not evaluated."
        ),
    )

    gate_assignment: GateAssignmentInput | None = Field(
        default=None,
        description=(
            "Requested flight gate assignment. "
            "None means assignment information is unavailable."
        ),
    )

    existing_gate_assignments: list[GateAssignmentInput] | None = Field(
        default=None,
        description=(
            "Existing gate assignments retrieved from the database. "
            "None means data is unavailable; an empty list means "
            "the database was checked and no assignments were found."
        ),
    )

    staff_availability_checks: list[StaffAvailabilityInput] | None = Field(
        default=None,
        description=(
            "Staff members whose availability must be checked. "
            "None means staff availability information was not supplied."
        ),
    )

    permission_request_id: str | None = None
    requested_by: str | None = None


class RuleResult(BaseModel):
    """Result produced by evaluating one operational rule."""

    rule_id: str

    rule_name: str

    triggered: bool

    severity: Literal["LOW", "MEDIUM", "HIGH"]

    message: str

    evaluation_status: Literal[
        "EVALUATED",
        "NOT_EVALUATED",
    ] = "EVALUATED"

class DecisionSupportResult(BaseModel):
    """Final advisory decision produced by RULE-009."""

    rule_id: str = "RULE-009"

    rule_name: str = "Grant/Hold/Delay Decision Support"

    decision: Literal["GRANT", "HOLD", "DELAY"]

    reasons: list[str] = Field(default_factory=list)

    evaluation_status: Literal[
        "EVALUATED",
        "NOT_EVALUATED",
    ] = "EVALUATED"

    advisory_only: bool = True

class RuleEvaluationResponse(BaseModel):
    """Complete response from the Rule Engine."""

    airport_code: str

    flight_number: str

    triggered_rules: int = Field(ge=0)

    results: list[RuleResult]

    advisory_only: bool = True

    decision_support: DecisionSupportResult | None = None
