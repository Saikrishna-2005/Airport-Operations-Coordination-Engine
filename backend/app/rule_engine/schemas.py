from typing import Literal

from pydantic import BaseModel, Field


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

    delay_minutes: int = Field(
        default=0,
        ge=0,
        description="Reported flight delay in minutes",
    )

    rainfall_mm: float = Field(
        default=0.0,
        ge=0,
        description="Reported rainfall in millimetres",
    )

    runway_available: bool | None = Field(
        default=None,
        description=(
            "Reported runway availability. "
            "True=available, False=unavailable, "
            "None=unknown or not evaluated."
        ),
    )


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


class RuleEvaluationResponse(BaseModel):
    """Complete response from the Rule Engine."""

    airport_code: str

    flight_number: str

    triggered_rules: int = Field(ge=0)

    results: list[RuleResult]

    advisory_only: bool = True