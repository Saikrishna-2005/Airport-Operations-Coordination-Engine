from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.dependencies import get_current_user

from app.database.runway_database import (
    initialize_runway_database,
    update_runway_status,
    get_runway_status,
    get_airport_runways,
)


router = APIRouter(
    prefix="/api/runways",
    tags=["Runway Management"],
)


# -----------------------------------------------
# REQUEST MODEL
# -----------------------------------------------

class RunwayStatusUpdate(BaseModel):
    airport_code: str = Field(
        min_length=3,
        max_length=4,
        pattern=r"^[A-Za-z]{3,4}$",
    )

    runway_code: str = Field(
        min_length=2,
        max_length=10,
    )

    status: str = Field(
        pattern=r"^(AVAILABLE|UNAVAILABLE|UNKNOWN)$",
    )

    reason: str | None = None


# -----------------------------------------------
# IDENTIFY AUTHENTICATED USER
# -----------------------------------------------

def get_user_identifier(current_user) -> str:

    if isinstance(current_user, dict):
        user_id = (
            current_user.get("user_id")
            or current_user.get("username")
            or current_user.get("sub")
        )
    else:
        user_id = (
            getattr(current_user, "user_id", None)
            or getattr(current_user, "username", None)
            or getattr(current_user, "sub", None)
        )

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Authenticated user identifier unavailable.",
        )

    return str(user_id)


# -----------------------------------------------
# UPDATE RUNWAY STATUS
# -----------------------------------------------

@router.put("/status")
def set_runway_status(
    request: RunwayStatusUpdate,
    current_user=Depends(get_current_user),
):
    """
    Record a runway status reported by an
    authenticated user.

    Authentication alone does not establish
    operational authority.
    """

    user_id = get_user_identifier(current_user)

    try:
        initialize_runway_database()

        result = update_runway_status(
            airport_code=request.airport_code,
            runway_code=request.runway_code,
            status=request.status,
            updated_by=user_id,
            reason=request.reason,
        )

        return {
            "success": True,
            "message": "Runway status recorded successfully.",
            "runway": result,
            "source": "MANUAL_USER_REPORT",
            "verified": False,
            "advisory_only": True,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


# -----------------------------------------------
# GET SPECIFIC RUNWAY STATUS
# -----------------------------------------------

@router.get("/{airport_code}/{runway_code}")
def read_runway_status(
    airport_code: str,
    runway_code: str,
    current_user=Depends(get_current_user),
):

    initialize_runway_database()

    result = get_runway_status(
        airport_code,
        runway_code,
    )

    return {
        "success": True,
        "runway": result,
        "source": (
            "MANUAL_USER_REPORT"
            if result["updated_at"]
            else "NO_RECORDED_STATUS"
        ),
        "verified": False,
        "advisory_only": True,
    }


# -----------------------------------------------
# GET ALL RUNWAYS FOR AN AIRPORT
# -----------------------------------------------

@router.get("/{airport_code}")
def read_airport_runways(
    airport_code: str,
    current_user=Depends(get_current_user),
):

    initialize_runway_database()

    runways = get_airport_runways(
        airport_code,
    )

    return {
        "success": True,
        "airport_code": airport_code.upper(),
        "total_runways": len(runways),
        "runways": runways,
        "source": "MANUAL_USER_REPORT",
        "verified": False,
        "advisory_only": True,
    }