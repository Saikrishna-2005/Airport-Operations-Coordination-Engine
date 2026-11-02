from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agents.workflow import build_airport_workflow


router = APIRouter(
    prefix="/api/ai",
    tags=["AI Agent"],
)


class AIPlanningRequest(BaseModel):
    airport: str = Field(
        min_length=3,
        max_length=4,
    )

    disruption: str = Field(
        min_length=1,
    )

    affected_flights: list[str] = Field(
        min_length=1,
    )

    gate_request: dict | None = None

    runway_code: str | None = Field(
        default=None,
        min_length=2,
        max_length=10,
        description="Runway identifier for availability evaluation",
    )


@router.post("/planning")
def generate_ai_plan(request: AIPlanningRequest):

    try:
        workflow_id = f"WF-{uuid4().hex[:8].upper()}"

        workflow = build_airport_workflow()

        result = workflow.invoke(
            {
                "workflow_id": workflow_id,
                "airport": request.airport,
                "disruption": request.disruption,
                "affected_flights": request.affected_flights,
                "gate_request": request.gate_request,
                "runway_code": request.runway_code,
            }
        )

        return {
            "success": True,
            "workflow_id": workflow_id,
            "status": result.get("status"),
            "planning_result": result.get("planning_result"),
            "gate_result": result.get("gate_result"),
            "rule_results": result.get("rule_results"),
        }

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="AI planning workflow failed. Check backend logs.",
        )