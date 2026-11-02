from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.dependencies import get_current_user
from app.core.permissions import require_roles

from app.database.staff_shift_management import (
    get_all_staff_shifts,
    get_shift_by_id,
    create_staff_shift,
    update_staff_shift,
    delete_staff_shift,
)


router = APIRouter(
    prefix="/staff/shifts",
    tags=["Staff Shift Management"],
)


# ============================================================
# REQUEST MODELS
# ============================================================

class ShiftTimingRequest(BaseModel):
    shift_date: date
    shift_start_time: str = Field(min_length=5, max_length=5)
    shift_end_time: str = Field(min_length=5, max_length=5)

    @field_validator("shift_start_time", "shift_end_time")
    @classmethod
    def validate_time(cls, value: str) -> str:
        parts = value.split(":")

        if (
            len(parts) != 2
            or len(parts[0]) != 2
            or len(parts[1]) != 2
            or not all(part.isdigit() for part in parts)
        ):
            raise ValueError("Time must use HH:MM format")

        hours, minutes = map(int, parts)

        if not (0 <= hours <= 23 and 0 <= minutes <= 59):
            raise ValueError("Invalid time value")

        return value

    @model_validator(mode="after")
    def validate_duration(self):
        if self.shift_start_time == self.shift_end_time:
            raise ValueError(
                "Shift start and end times cannot be equal"
            )

        return self


class ShiftCreateRequest(ShiftTimingRequest):
    staff_id: str = Field(min_length=1, max_length=50)

    @field_validator("staff_id")
    @classmethod
    def validate_staff_id(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Staff ID cannot be empty")

        return value


class ShiftUpdateRequest(ShiftTimingRequest):
    pass


# ============================================================
# HELPERS
# ============================================================

def to_minutes(value: str) -> int:
    hours, minutes = map(int, value.split(":"))
    return hours * 60 + minutes


def get_shift_minutes(request: ShiftTimingRequest):
    start_minute = to_minutes(request.shift_start_time)
    end_minute = to_minutes(request.shift_end_time)

    if end_minute < start_minute:
        end_minute += 1440

    return start_minute, end_minute


def handle_shift_error(error: ValueError):
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=str(error),
    ) from error


# ============================================================
# GET ALL SHIFTS — AUTHENTICATED USERS
# GET /staff/shifts
#
# Optional airport filter:
# GET /staff/shifts?airport_code=HYD
# ============================================================

@router.get("")
def list_staff_shifts(
    airport_code: str | None = None,
    current_user: dict = Depends(get_current_user),
):
    try:
        shifts = get_all_staff_shifts(
            airport_code=airport_code
        )

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error

    normalized_airport_code = (
        airport_code.strip().upper()
        if airport_code is not None
        else None
    )

    return {
        "success": True,
        "airport_code": normalized_airport_code,
        "total_shifts": len(shifts),
        "shifts": shifts,
    }


# ============================================================
# GET ONE SHIFT — AUTHENTICATED USERS
# GET /staff/shifts/{shift_id}
# ============================================================

@router.get("/{shift_id}")
def retrieve_staff_shift(
    shift_id: int,
    current_user: dict = Depends(get_current_user),
):
    shift = get_shift_by_id(shift_id)

    if shift is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shift not found",
        )

    return {
        "success": True,
        "shift": shift,
    }


# ============================================================
# CREATE SHIFT — ADMIN ONLY
# POST /staff/shifts
# ============================================================

@router.post("", status_code=status.HTTP_201_CREATED)
def add_staff_shift(
    request: ShiftCreateRequest,
    current_user: dict = Depends(require_roles("admin")),
):
    start_minute, end_minute = get_shift_minutes(request)

    try:
        shift = create_staff_shift(
            staff_id=request.staff_id,
            shift_date=request.shift_date.isoformat(),
            start_minute=start_minute,
            end_minute=end_minute,
        )

    except ValueError as error:
        handle_shift_error(error)

    return {
        "success": True,
        "message": "Staff shift created successfully",
        "shift": shift,
    }


# ============================================================
# UPDATE SHIFT — ADMIN ONLY
# PUT /staff/shifts/{shift_id}
# ============================================================

@router.put("/{shift_id}")
def edit_staff_shift(
    shift_id: int,
    request: ShiftUpdateRequest,
    current_user: dict = Depends(require_roles("admin")),
):
    start_minute, end_minute = get_shift_minutes(request)

    try:
        shift = update_staff_shift(
            shift_id=shift_id,
            shift_date=request.shift_date.isoformat(),
            start_minute=start_minute,
            end_minute=end_minute,
        )

    except ValueError as error:
        handle_shift_error(error)

    if shift is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shift not found",
        )

    return {
        "success": True,
        "message": "Staff shift updated successfully",
        "shift": shift,
    }


# ============================================================
# DELETE SHIFT — ADMIN ONLY
# DELETE /staff/shifts/{shift_id}
# ============================================================

@router.delete("/{shift_id}")
def remove_staff_shift(
    shift_id: int,
    current_user: dict = Depends(require_roles("admin")),
):
    try:
        deleted = delete_staff_shift(shift_id)

    except ValueError as error:
        handle_shift_error(error)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shift not found",
        )

    return {
        "success": True,
        "message": "Staff shift deleted successfully",
        "shift_id": shift_id,
    }