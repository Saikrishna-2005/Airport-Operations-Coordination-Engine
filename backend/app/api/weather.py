from fastapi import APIRouter, Depends, HTTPException, status
from app.tools.airport_lookup import search_airports

from app.tools.weather_data_tool import get_weather_data
from app.core.dependencies import get_current_user
from app.rule_engine.weather_adapter import evaluate_airport_weather

from pydantic import BaseModel, Field

from app.database.airport_monitoring import (
    create_airport_monitoring_table,
    add_monitored_airport,
    list_monitored_airports,
    remove_monitored_airport,
)

router = APIRouter(prefix="/weather", tags=["Weather"])

# --------------------------------------------------
# AIRPORT MONITORING REQUEST MODEL
# --------------------------------------------------

class AddAirportRequest(BaseModel):
    airport_code: str = Field(
        ...,
        min_length=3,
        max_length=3,
        pattern=r"^[A-Za-z]{3}$"
    )


# --------------------------------------------------
# 1. HANDLE WEATHER API ERRORS
# --------------------------------------------------

def handle_weather_error(result: dict):
    reason = result.get(
        "reason",
        "Weather information unavailable"
    )

    if reason.startswith((
        "Unsupported airport code",
        "Airport code not found",
        "Airport code must",
    )):
        raise HTTPException(
            status_code=400,
            detail=reason
        )

    raise HTTPException(
        status_code=503,
        detail=reason
    )


# --------------------------------------------------
# 2. CURRENT WEATHER API
# --------------------------------------------------

@router.get("/current/{airport_code}")
def get_current_weather(
    airport_code: str,
    current_user=Depends(get_current_user)
):
    result = get_weather_data(airport_code)

    if not result["success"]:
        handle_weather_error(result)

    return result


# --------------------------------------------------
# 3. WEATHER RISK API
# --------------------------------------------------

@router.get("/risk/{airport_code}")
def get_weather_risk(
    airport_code: str,
    current_user=Depends(get_current_user)
):
    weather = get_weather_data(airport_code)

    if not weather["success"]:
        handle_weather_error(weather)

    # Required weather measurements
    required_fields = [
        "rain_mm",
        "visibility_m",
        "wind_speed_kmh"
    ]

    missing_fields = [
        field
        for field in required_fields
        if weather.get(field) is None
    ]

    if missing_fields:
        raise HTTPException(
            status_code=503,
            detail={
                "message": (
                    "Weather risk evaluation unavailable "
                    "because required measurements are missing."
                ),
                "missing_fields": missing_fields
            }
        )

    # Evaluate weather using Python Rule Engine
    risk = evaluate_airport_weather(
        airport_code=weather["airport_code"],
        rainfall_mm=weather["rain_mm"],
        visibility_m=weather["visibility_m"],
        wind_speed_kmh=weather["wind_speed_kmh"]
    )

    return {
        "success": True,
        "airport_code": weather["airport_code"],
        "airport_name": weather["airport_name"],
        "observation_time": weather.get("observation_time"),
        "risk": risk,
        "weather": {
            "rain_mm": weather["rain_mm"],
            "visibility_m": weather["visibility_m"],
            "wind_speed_kmh": weather["wind_speed_kmh"]
        },
        "source": weather.get("source"),
        "advisory_only": True
    }

# --------------------------------------------------
# 4. ADD AIRPORT TO MONITORING LIST
# --------------------------------------------------

@router.post("/airports", status_code=status.HTTP_201_CREATED)
def add_airport(
    request: AddAirportRequest,
    current_user=Depends(get_current_user)
):
    create_airport_monitoring_table()

    # The existing authentication dependency determines
    # the identity of the logged-in user.
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
            status_code=500,
            detail="Authenticated user identifier unavailable."
        )

    result = add_monitored_airport(
        airport_code=request.airport_code,
        added_by=str(user_id)
    )

    if not result["success"]:
        reason = result["reason"]

        if "already monitored" in reason:
            raise HTTPException(
                status_code=409,
                detail=reason
            )

        raise HTTPException(
            status_code=400,
            detail=reason
        )

    return result


# --------------------------------------------------
# SEARCH AIRPORTS WORLDWIDE
# --------------------------------------------------

@router.get("/airports/search")
def search_global_airports(
    q: str,
    limit: int = 15,
    current_user=Depends(get_current_user)
):
    """
    Search airports by name, city, country code,
    or three-letter IATA code.
    """

    result = search_airports(
        query=q,
        limit=limit
    )

    if not result["success"]:
        raise HTTPException(
            status_code=400,
            detail=result["reason"]
        )

    return result

# --------------------------------------------------
# 5. LIST MONITORED AIRPORTS
# --------------------------------------------------

@router.get("/airports")
def get_monitored_airports(
    current_user=Depends(get_current_user)
):
    create_airport_monitoring_table()

    return list_monitored_airports()


# --------------------------------------------------
# 6. REMOVE MONITORED AIRPORT
# --------------------------------------------------

@router.delete("/airports/{airport_code}")
def delete_monitored_airport(
    airport_code: str,
    current_user=Depends(get_current_user)
):
    result = remove_monitored_airport(airport_code)

    if not result["success"]:
        raise HTTPException(
            status_code=404,
            detail=result["reason"]
        )

    return result