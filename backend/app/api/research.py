"""Research Agent API endpoints integrated into the airport backend."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.research_agent.agent import run_research_agent
from app.research_agent.config import settings as research_settings
from app.research_agent.schemas import (
    DataMode, DisruptionType, ResearchRequest, ResearchResult,
)

router = APIRouter(prefix="/api/research", tags=["Research Agent"])


class ResearchExecutionRequest(BaseModel):
    airport_code: str = Field(min_length=3, max_length=4)
    disruption_description: str = Field(min_length=1, max_length=2000)
    affected_flights: list[str] = Field(default_factory=list, max_length=50)
    research_requirements: list[str] = Field(
        default_factory=lambda: [
            "current weather conditions, wind, visibility and precipitation",
            "flight aircraft state and status for affected flights",
        ],
        min_length=1, max_length=20,
    )
    planning_objective: str | None = Field(default=None, max_length=1000)
    data_mode: DataMode | None = None


def _disruption_type(description: str) -> DisruptionType:
    value = description.lower()
    if any(word in value for word in ("weather", "rain", "wind", "storm", "fog", "visibility")):
        return DisruptionType.weather
    if any(word in value for word in ("delay", "late", "schedule")):
        return DisruptionType.delay
    if any(word in value for word in ("runway", "closure", "surface")):
        return DisruptionType.runway
    return DisruptionType.other


@router.post("/execute", response_model=ResearchResult)
def execute_research(request: ResearchExecutionRequest) -> ResearchResult:
    """Run evidence collection and synthesis. Output is advisory only."""
    try:
        research_request = ResearchRequest(
            request_id=str(uuid4()),
            workflow_id=f"RESEARCH-{uuid4().hex[:10].upper()}",
            airport_code=request.airport_code,
            disruption_type=_disruption_type(request.disruption_description),
            disruption_description=request.disruption_description,
            affected_flights=request.affected_flights,
            research_requirements=request.research_requirements,
            planning_objective=request.planning_objective,
            as_of=datetime.now(timezone.utc),
            data_mode=request.data_mode or DataMode(research_settings.DATA_MODE),
        )
        return run_research_agent(research_request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Research Agent execution failed ({type(exc).__name__}). Check backend logs.",
        ) from exc
