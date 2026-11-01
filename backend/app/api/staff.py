from datetime import date, datetime, timedelta
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from app.core.dependencies import get_current_user
from app.core.permissions import require_roles

from app.database.staff_database import get_staff_assignment_history
from app.tools.staff_availability_tool import check_staff_availability
from app.tools.staff_allocation_tool import allocate_staff


router = APIRouter(
    prefix="/staff",
    tags=["Staff Operations"],
)


# ============================================================
# STAFF AVAILABILITY REQUEST MODEL
# ============================================================

class StaffAvailabilityRequest(BaseModel):
    staff_id: str = Field(min_length=1, max_length=50)
    airport_code: str = Field(min_length=3, max_length=3)
    requested_date: date
    start_time: str
    end_time: str

    @field_validator("staff_id")
    @classmethod
    def validate_staff_id(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Staff ID cannot be empty")

        return value

    @field_validator("airport_code")
    @classmethod
    def validate_airport_code(cls, value: str) -> str:
        value = value.strip().upper()

        if (
            len(value) != 3
            or not value.isascii()
            or not value.isalpha()
        ):
            raise ValueError(
                "Airport code must contain exactly 3 English letters"
            )

        return value

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_time(cls, value: str) -> str:
        try:
            parsed = datetime.strptime(value, "%H:%M")
        except ValueError:
            raise ValueError("Time must use HH:MM format")

        return parsed.strftime("%H:%M")


# ============================================================
# STAFF ALLOCATION REQUEST MODEL
# ============================================================

class StaffAllocationRequest(BaseModel):
    staff_id: str = Field(min_length=1, max_length=50)
    airport_code: str = Field(min_length=3, max_length=4)
    assignment_date: date
    start_time: str
    end_time: str
    task_name: str = Field(min_length=1, max_length=200)
    gate_id: str | None = Field(default=None, max_length=50)

    @field_validator("staff_id", "task_name")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("This field cannot be empty")

        return value

    @field_validator("airport_code")
    @classmethod
    def validate_airport_code(cls, value: str) -> str:
        value = value.strip().upper()

        if (
            not value.isascii()
            or not value.isalpha()
            or len(value) not in (3, 4)
        ):
            raise ValueError(
                "Airport code must contain 3 or 4 English letters"
            )

        return value

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_allocation_time(cls, value: str) -> str:
        try:
            parsed = datetime.strptime(value, "%H:%M")
        except ValueError:
            raise ValueError("Time must use HH:MM format")

        return parsed.strftime("%H:%M")

    @field_validator("gate_id")
    @classmethod
    def validate_gate_id(cls, value: str | None) -> str | None:
        if value is None:
            return None

        return value.strip() or None


# ============================================================
# STAFF AVAILABILITY API
# POST /staff/availability
#
# Admin    - Allowed
# Operator - Allowed
# Pilot    - Allowed
# ============================================================

@router.post("/availability")
def staff_availability(
    request: StaffAvailabilityRequest,
    current_user=Depends(get_current_user),
):
    start = datetime.combine(
        request.requested_date,
        datetime.strptime(
            request.start_time,
            "%H:%M",
        ).time(),
    )

    end = datetime.combine(
        request.requested_date,
        datetime.strptime(
            request.end_time,
            "%H:%M",
        ).time(),
    )

    if end == start:
        raise HTTPException(
            status_code=422,
            detail="Start time and end time cannot be the same",
        )

    if end < start:
        end += timedelta(days=1)

    duration = end - start

    if duration > timedelta(hours=24):
        raise HTTPException(
            status_code=422,
            detail="Requested duration cannot exceed 24 hours",
        )

    return check_staff_availability(
        staff_id=request.staff_id,
        airport_code=request.airport_code,
        requested_date=request.requested_date.isoformat(),
        start_time=request.start_time,
        end_time=request.end_time,
    )


# ============================================================
# STAFF ALLOCATION API
# POST /staff/allocate
#
# Admin    - Allowed
# Operator - Forbidden
# Pilot    - Forbidden
# ============================================================

@router.post("/allocate")
def create_staff_allocation(
    request: StaffAllocationRequest,
    current_user: dict = Depends(require_roles("admin")),
):
    start = datetime.strptime(
        request.start_time,
        "%H:%M",
    )

    end = datetime.strptime(
        request.end_time,
        "%H:%M",
    )

    if end <= start:
        raise HTTPException(
            status_code=422,
            detail=(
                "Staff allocation currently supports "
                "same-day intervals only"
            ),
        )

    result = allocate_staff(
        staff_id=request.staff_id,
        assignment_date=request.assignment_date.isoformat(),
        start_time=request.start_time,
        end_time=request.end_time,
        task_name=request.task_name,
        gate_id=request.gate_id,
        airport_code=request.airport_code,
    )

    if not result["success"]:
        raise HTTPException(
            status_code=409,
            detail=result["reason"],
        )

    return result


# ============================================================
# STAFF ASSIGNMENT HISTORY API
# GET /staff/assignments/history
#
# Admin    - Airport history + unknown historical records
# Operator - Airport history
# Pilot    - Airport history
#
# NOTE:
# Unknown historical records require admin authorization.
# ============================================================

@router.get("/assignments/history")
def staff_assignment_history(
    airport_code: str | None = Query(default=None),
    staff_id: str | None = Query(default=None),
    include_unknown: bool = Query(default=False),
    current_user: dict = Depends(get_current_user),
):
    # --------------------------------------------------------
    # VALIDATE AIRPORT CODE
    # --------------------------------------------------------

    if airport_code is not None:
        airport_code = airport_code.strip().upper()

        if not re.fullmatch(r"[A-Z]{3,4}", airport_code):
            raise HTTPException(
                status_code=422,
                detail="Airport code must contain 3 or 4 English letters",
            )

    # --------------------------------------------------------
    # VALIDATE OPTIONAL STAFF ID
    # --------------------------------------------------------

    if staff_id is not None:
        staff_id = staff_id.strip()

        if not staff_id or len(staff_id) > 50:
            raise HTTPException(
                status_code=422,
                detail="Staff ID must contain 1 to 50 characters",
            )

    # --------------------------------------------------------
    # REQUIRE AN EXPLICIT HISTORY SCOPE
    # --------------------------------------------------------

    if airport_code is None and not include_unknown:
        raise HTTPException(
            status_code=422,
            detail=(
                "Provide airport_code or set "
                "include_unknown=true"
            ),
        )

    if airport_code is not None and include_unknown:
        raise HTTPException(
            status_code=422,
            detail=(
                "Choose either airport_code or "
                "include_unknown=true, not both"
            ),
        )

    # --------------------------------------------------------
    # ADMIN-ONLY ACCESS TO UNKNOWN HISTORICAL RECORDS
    # --------------------------------------------------------

    if include_unknown:
        # Reuse the project's existing role dependency.
        # The endpoint's authenticated user is already available.
        # Authorization is enforced below using the role returned
        # by get_current_user.
        if not isinstance(current_user, dict):
            raise HTTPException(
                status_code=403,
                detail="Administrator access required",
            )

        user_role = str(
            current_user.get("role", "")
        ).strip().lower()

        if user_role != "admin":
            raise HTTPException(
                status_code=403,
                detail="Only administrators can view unknown-airport history",
            )

    # --------------------------------------------------------
    # RETRIEVE ASSIGNMENT HISTORY
    # --------------------------------------------------------

    assignments = get_staff_assignment_history(
        airport_code=airport_code,
        staff_id=staff_id,
        include_unknown=include_unknown,
    )

    return {
        "success": True,
        "airport_code": airport_code,
        "include_unknown": include_unknown,
        "staff_id": staff_id,
        "total_assignments": len(assignments),
        "assignments": assignments,
    }