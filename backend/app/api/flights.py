from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)

from pydantic import BaseModel, Field

from app.core.dependencies import get_current_user

from app.database.flight_database import (
    create_flight,
    get_all_flights,
    get_flight_by_id,
    update_flight,
    delete_flight,
    get_flight_operational_pulse,
    calculate_flight_dependency_impacts,
    create_flight_dependency,
    get_flight_dependencies,
    delete_flight_dependency,
    get_flight_risk_factors,
)

from app.schemas.flight import (
    FlightCreate,
    FlightUpdate,
)


# ============================================================
# FLIGHT IMPACT SIMULATION REQUEST
# ============================================================

class FlightImpactSimulationRequest(BaseModel):

    flight_id: int = Field(gt=0)

    additional_delay_minutes: int = Field(
        ge=0,
        le=1440,
    )


# ============================================================
# FLIGHT DEPENDENCY CREATE REQUEST
# ============================================================

class FlightDependencyCreateRequest(BaseModel):

    flight_id: int = Field(gt=0)

    dependent_flight_id: int = Field(gt=0)

    dependency_type: str = Field(
        min_length=2,
        max_length=50,
    )

    minimum_turnaround_minutes: int = Field(
        default=0,
        ge=0,
        le=1440,
    )


# ============================================================
# FLIGHT OPERATIONS ROUTER
# ============================================================

router = APIRouter(
    prefix="/api/flights",
    tags=["Flight Operations"],
    dependencies=[Depends(get_current_user)],
)


# ============================================================
# ROLE-BASED ACCESS CONTROL
# ============================================================

def require_flight_role(*allowed_roles):

    def check_role(
        current_user: dict = Depends(get_current_user),
    ):

        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "You do not have permission "
                    "for this operation"
                ),
            )

        return current_user

    return check_role


# ============================================================
# GET ALL FLIGHTS
# ============================================================

@router.get("/")
def list_flights(
    flight_status: str | None = Query(
        default=None,
        alias="status",
    ),
    airport: str | None = None,
):

    flights = get_all_flights()

    if flight_status:
        flights = [
            flight
            for flight in flights
            if flight["status"] == flight_status.upper()
        ]

    if airport:

        code = airport.upper()

        flights = [
            flight
            for flight in flights
            if flight["origin_code"] == code
            or flight["destination_code"] == code
        ]

    return flights


# ============================================================
# GET DYNAMIC OPERATIONAL PULSE
# ============================================================

@router.get("/operational-pulse")
def operational_pulse():

    return get_flight_operational_pulse()


# ============================================================
# DYNAMIC FLIGHT IMPACT SIMULATOR
# ============================================================

@router.post("/simulate-impact")
def simulate_flight_impact(
    request: FlightImpactSimulationRequest,
):

    flight = get_flight_by_id(
        request.flight_id
    )

    if flight is None:
        raise HTTPException(
            status_code=404,
            detail="Flight not found",
        )

    impacts = calculate_flight_dependency_impacts(
        flight_id=request.flight_id,
        additional_delay_minutes=(
            request.additional_delay_minutes
        ),
    )

    affected_flights = [
        impact
        for impact in impacts
        if impact["impact_status"] == "AFFECTED"
    ]

    total_affected = len(affected_flights)

    maximum_impact = max(
        (
            impact["impact_minutes"]
            for impact in affected_flights
        ),
        default=0,
    )

    return {
        "flight_id": request.flight_id,
        "flight_number": flight["flight_number"],
        "additional_delay_minutes": (
            request.additional_delay_minutes
        ),
        "total_dependencies": len(impacts),
        "total_affected_flights": total_affected,
        "maximum_impact_minutes": maximum_impact,
        "affected_flight_ids": [
            impact["dependent_flight_id"]
            for impact in affected_flights
        ],
        "dependency_impacts": impacts,
        "simulation_only": True,
        "message": (
            "Simulation completed. "
            "No flight records were modified."
        ),
    }


# ============================================================
# CREATE FLIGHT DEPENDENCY
# ============================================================

@router.post(
    "/dependencies",
    status_code=status.HTTP_201_CREATED,
)
def add_flight_dependency(
    request: FlightDependencyCreateRequest,
    current_user: dict = Depends(
        require_flight_role("admin", "operator")
    ),
):

    try:

        dependency = create_flight_dependency(
            flight_id=request.flight_id,
            dependent_flight_id=request.dependent_flight_id,
            dependency_type=request.dependency_type,
            minimum_turnaround_minutes=(
                request.minimum_turnaround_minutes
            ),
        )

        return dependency

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


# ============================================================
# DELETE FLIGHT DEPENDENCY
# ============================================================

@router.delete("/dependencies/{dependency_id}")
def remove_flight_dependency(
    dependency_id: int,
    current_user: dict = Depends(
        require_flight_role("admin", "operator")
    ),
):

    deleted = delete_flight_dependency(
        dependency_id
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Flight dependency not found",
        )

    return {
        "message": "Flight dependency deleted successfully",
        "dependency_id": dependency_id,
    }


# ============================================================
# GET FLIGHT DEPENDENCIES
# ============================================================

@router.get("/{flight_id}/dependencies")
def list_flight_dependencies(
    flight_id: int,
):

    flight = get_flight_by_id(flight_id)

    if flight is None:
        raise HTTPException(
            status_code=404,
            detail="Flight not found",
        )

    dependencies = get_flight_dependencies(
        flight_id
    )

    return dependencies


# ============================================================
# GET DIRECT FLIGHT DEPENDENCY IMPACTS
# ============================================================

@router.get("/{flight_id}/dependency-impacts")
def get_dependency_impacts(
    flight_id: int,
    additional_delay_minutes: int = Query(
        default=0,
        ge=0,
        le=1440,
    ),
):

    flight = get_flight_by_id(flight_id)

    if flight is None:
        raise HTTPException(
            status_code=404,
            detail="Flight not found",
        )

    impacts = calculate_flight_dependency_impacts(
        flight_id=flight_id,
        additional_delay_minutes=additional_delay_minutes,
    )

    return {
        "flight_id": flight_id,
        "flight_number": flight["flight_number"],
        "additional_delay_minutes": additional_delay_minutes,
        "total_dependencies": len(impacts),
        "dependency_impacts": impacts,
    }

# ============================================================
# GET DYNAMIC FLIGHT RISK
# ============================================================

@router.get("/{flight_id}/risk")
def get_flight_risk(flight_id: int):

    flight = get_flight_by_id(flight_id)

    if flight is None:
        raise HTTPException(
            status_code=404,
            detail="Flight not found",
        )

    risk_score = int(flight["risk_score"] or 0)

    if risk_score >= 75:
        risk_level = "CRITICAL"
    elif risk_score >= 50:
        risk_level = "HIGH"
    elif risk_score >= 25:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    factors = get_flight_risk_factors(flight_id)

    return {
        "flight_id": flight_id,
        "flight_number": flight["flight_number"],
        "risk_score": risk_score,
        "risk_level": risk_level,
        "risk_factors": factors,
    }


# ============================================================
# GET FLIGHT BY ID
# ============================================================

@router.get("/{flight_id}")
def get_flight(flight_id: int):

    flight = get_flight_by_id(flight_id)

    if flight is None:
        raise HTTPException(
            status_code=404,
            detail="Flight not found",
        )

    return flight


# ============================================================
# CREATE FLIGHT
# ============================================================

@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
)
def add_flight(
    flight: FlightCreate,
    current_user: dict = Depends(
        require_flight_role("admin", "operator")
    ),
):

    return create_flight(flight)


# ============================================================
# UPDATE FLIGHT
# ============================================================

@router.patch("/{flight_id}")
def modify_flight(
    flight_id: int,
    flight: FlightUpdate,
    current_user: dict = Depends(
        require_flight_role("admin", "operator")
    ),
):

    try:

        updated = update_flight(
            flight_id,
            flight,
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    if updated is None:
        raise HTTPException(
            status_code=404,
            detail="Flight not found",
        )

    return updated


# ============================================================
# DELETE FLIGHT
# ============================================================

@router.delete("/{flight_id}")
def remove_flight(
    flight_id: int,
    current_user: dict = Depends(
        require_flight_role("admin")
    ),
):

    deleted = delete_flight(flight_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Flight not found",
        )

    return {
        "message": "Flight deleted successfully",
        "flight_id": flight_id,
    }