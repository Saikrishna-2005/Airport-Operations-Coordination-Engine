from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.dependencies import get_current_user
from app.core.permissions import require_roles

from app.database.staff_management import (
    get_all_staff,
    get_staff_by_id,
    create_staff_member,
    update_staff_member,
    delete_staff_member,
)


router = APIRouter(
    prefix="/staff/members",
    tags=["Staff Management"],
)


# ============================================================
# REQUEST MODELS
# ============================================================

class StaffCreateRequest(BaseModel):
    staff_id: str = Field(min_length=1, max_length=50)
    full_name: str = Field(min_length=1, max_length=150)
    role: str = Field(min_length=1, max_length=100)
    employment_status: str = Field(min_length=1, max_length=50)
    airport_code: str = Field(min_length=3, max_length=3)

    # Mandatory initial shift
    shift_date: date
    shift_start_time: str
    shift_end_time: str

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

    @field_validator("staff_id", "full_name", "role")
    @classmethod
    def validate_text(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Field cannot be empty")

        return value

    @field_validator("employment_status")
    @classmethod
    def validate_employment_status(cls, value: str) -> str:
        value = value.strip().lower()

        if value not in {"active", "inactive"}:
            raise ValueError(
                "Employment status must be active or inactive"
            )

        return value

    @field_validator("shift_start_time", "shift_end_time")
    @classmethod
    def validate_shift_time(cls, value: str) -> str:
        parts = value.split(":")

        if len(parts) != 2:
            raise ValueError("Time must use HH:MM format")

        try:
            hours, minutes = map(int, parts)
        except ValueError:
            raise ValueError("Time must use HH:MM format")

        if not (0 <= hours <= 23 and 0 <= minutes <= 59):
            raise ValueError("Invalid shift time")

        if (
            len(parts[0]) != 2
            or len(parts[1]) != 2
            or not all(part.isdigit() for part in parts)
        ):
            raise ValueError("Time must use HH:MM format")

        return value

    @model_validator(mode="after")
    def validate_shift_duration(self):
        start = self._to_minutes(self.shift_start_time)
        end = self._to_minutes(self.shift_end_time)

        if end <= start:
            end += 1440

        # Equal clock times would represent a 24-hour shift.
        # Reject this ambiguity for initial shift creation.
        if self.shift_start_time == self.shift_end_time:
            raise ValueError(
                "Shift start and end times cannot be equal"
            )

        return self

    @staticmethod
    def _to_minutes(value: str) -> int:
        hours, minutes = map(int, value.split(":"))
        return hours * 60 + minutes


class StaffUpdateRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=150)
    role: str = Field(min_length=1, max_length=100)
    employment_status: str = Field(min_length=1, max_length=50)

    @field_validator("full_name", "role")
    @classmethod
    def validate_text(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Field cannot be empty")

        return value

    @field_validator("employment_status")
    @classmethod
    def validate_employment_status(cls, value: str) -> str:
        value = value.strip().lower()

        if value not in {"active", "inactive"}:
            raise ValueError(
                "Employment status must be active or inactive"
            )

        return value


# ============================================================
# GET ALL STAFF
# GET /staff/members
# ============================================================

@router.get("")
def list_staff_members(
    airport_code: str | None = None,
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieve staff members.

    When airport_code is provided, return staff
    assigned to that airport.

    Without airport_code, return all staff.
    """

    try:
        staff = get_all_staff(airport_code=airport_code)

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    return {
        "success": True,
        "airport_code": airport_code.strip().upper() if airport_code else None,
        "total_staff": len(staff),
        "staff": staff,
    }


# ============================================================
# GET ONE STAFF MEMBER
# GET /staff/members/{staff_id}
# ============================================================

@router.get("/{staff_id}")
def get_staff_member(
    staff_id: str,
    current_user: dict = Depends(get_current_user),
):
    staff = get_staff_by_id(staff_id)

    if staff is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff member not found",
        )

    return {
        "success": True,
        "staff": staff,
    }


# ============================================================
# ADD STAFF WITH INITIAL SHIFT — ADMIN ONLY
# POST /staff/members
# ============================================================

@router.post("", status_code=status.HTTP_201_CREATED)
def add_staff_member(
    request: StaffCreateRequest,
    current_user: dict = Depends(require_roles("admin")),
):
    start_minute = StaffCreateRequest._to_minutes(
        request.shift_start_time
    )

    end_minute = StaffCreateRequest._to_minutes(
        request.shift_end_time
    )

    # Overnight shift
    if end_minute < start_minute:
        end_minute += 1440

    try:
        result = create_staff_member(
            staff_id=request.staff_id,
            full_name=request.full_name,
            role=request.role,
            employment_status=request.employment_status,
            shift_date=request.shift_date.isoformat(),
            start_minute=start_minute,
            end_minute=end_minute,
            airport_code=request.airport_code,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=result["reason"],
        )

    return result


# ============================================================
# UPDATE STAFF DETAILS — ADMIN ONLY
# PUT /staff/members/{staff_id}
# ============================================================

@router.put("/{staff_id}")
def edit_staff_member(
    staff_id: str,
    request: StaffUpdateRequest,
    current_user: dict = Depends(require_roles("admin")),
):
    result = update_staff_member(
        staff_id=staff_id,
        full_name=request.full_name,
        role=request.role,
        employment_status=request.employment_status,
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["reason"],
        )

    return result


# ============================================================
# DELETE STAFF — ADMIN ONLY
# DELETE /staff/members/{staff_id}
# ============================================================

@router.delete("/{staff_id}")
def remove_staff_member(
    staff_id: str,
    current_user: dict = Depends(require_roles("admin")),
):
    result = delete_staff_member(staff_id)

    if not result["success"]:
        reason = result["reason"]

        if reason == "Staff member not found":
            status_code = status.HTTP_404_NOT_FOUND
        else:
            status_code = status.HTTP_409_CONFLICT

        raise HTTPException(
            status_code=status_code,
            detail=reason,
        )

    return result