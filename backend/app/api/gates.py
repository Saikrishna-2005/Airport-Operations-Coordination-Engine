from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.dependencies import get_current_user

from app.tools.gate_availability_tool import (
    GateAvailabilityRequest,
    GateAvailabilityResult,
    check_gate_availability,
    find_alternative_gates,
)


router = APIRouter(
    prefix="/gates",
    tags=["Gate Availability"],
)


class GateCheckRequest(GateAvailabilityRequest):
    candidate_gates: list[str] = Field(
        default_factory=list,
        max_length=50,
    )


@router.post(
    "/availability",
    response_model=GateAvailabilityResult,
)
def check_gate(
    request: GateCheckRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Check gate conflicts and suggest conflict-free candidates.

    This endpoint does not reserve or reassign gates.
    """

    gate_request = GateAvailabilityRequest(
        airport_code=request.airport_code,
        flight_number=request.flight_number,
        gate_id=request.gate_id,
        start_minute=request.start_minute,
        end_minute=request.end_minute,
    )

    result = check_gate_availability(gate_request)

    if not result.available and request.candidate_gates:
        result.alternative_gates = find_alternative_gates(
            gate_request,
            request.candidate_gates,
        )

    return result