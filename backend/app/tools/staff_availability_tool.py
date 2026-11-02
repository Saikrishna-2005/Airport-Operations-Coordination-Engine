from datetime import date, datetime, timedelta

from app.database.connection import get_db_connection

from app.database.staff_database import (
    get_staff_member,
    get_staff_shifts,
    get_staff_assignments,
)


# ============================================================
# HELPER: CONVERT DATE AND MINUTES TO DATETIME
# ============================================================

def _to_datetime(day: str, minute: int) -> datetime:
    """
    Convert a date and minute offset into a datetime.

    Minute offsets greater than 1440 represent time
    on the following day.
    """
    return datetime.combine(
        date.fromisoformat(day),
        datetime.min.time(),
    ) + timedelta(minutes=minute)


# ============================================================
# HELPER: CHECK TIME OVERLAP
# ============================================================

def _overlaps(start_a, end_a, start_b, end_b) -> bool:
    """
    Return True when two time intervals overlap.

    Intervals are treated as [start, end), so an
    assignment ending at 14:00 does not conflict
    with one starting at 14:00.
    """
    return start_a < end_b and start_b < end_a


# ============================================================
# HELPER: VERIFY ACTIVE AIRPORT ASSIGNMENT
# ============================================================

def _is_staff_assigned_to_airport(
    staff_id: str,
    airport_code: str,
) -> bool:
    """
    Check whether the staff member has an active
    assignment to the requested airport.
    """

    connection = get_db_connection()

    try:
        row = connection.execute(
            """
            SELECT 1
            FROM staff_airport_assignments
            WHERE staff_id = ?
              AND airport_code = ?
              AND assignment_status = 'active'
            LIMIT 1
            """,
            (staff_id, airport_code),
        ).fetchone()

        return row is not None

    finally:
        connection.close()


# ============================================================
# MAIN FUNCTION: CHECK STAFF AVAILABILITY
# ============================================================

def check_staff_availability(
    staff_id: str,
    requested_date: str,
    start_time: str,
    end_time: str,
    airport_code: str,
) -> dict:
    """
    Check whether a staff member is available
    for a requested airport, date, and time interval.

    Validations:
    1. Request date and time
    2. Airport code
    3. Staff existence
    4. Employment status
    5. Active airport assignment
    6. Scheduled shift coverage
    7. Existing assignment conflicts

    This function does not allocate staff.
    """

    # --------------------------------------------------------
    # 1. VALIDATE STAFF ID AND AIRPORT CODE
    # --------------------------------------------------------

    staff_id = staff_id.strip()
    airport_code = airport_code.strip().upper()

    if not staff_id:
        raise ValueError("Staff ID cannot be empty")

    if (
        len(airport_code) != 3
        or not airport_code.isascii()
        or not airport_code.isalpha()
    ):
        raise ValueError(
            "Airport code must contain exactly 3 English letters"
        )

    # --------------------------------------------------------
    # 2. VALIDATE REQUEST DATE AND TIME
    # --------------------------------------------------------

    try:
        request_day = date.fromisoformat(requested_date)

        start_clock = datetime.strptime(
            start_time, "%H:%M"
        ).time()

        end_clock = datetime.strptime(
            end_time, "%H:%M"
        ).time()

    except ValueError:
        raise ValueError(
            "Invalid date or time format. "
            "Use YYYY-MM-DD and HH:MM."
        )

    request_start = datetime.combine(
        request_day, start_clock
    )

    request_end = datetime.combine(
        request_day, end_clock
    )

    # Preserve existing overnight interval support.
    if request_end <= request_start:
        request_end += timedelta(days=1)

    # --------------------------------------------------------
    # 3. CHECK STAFF EXISTENCE
    # --------------------------------------------------------

    staff = get_staff_member(staff_id)

    if staff is None:
        return {
            "staff_id": staff_id,
            "airport_code": airport_code,
            "available": False,
            "reason": "Staff member not found",
        }

    # --------------------------------------------------------
    # 4. CHECK EMPLOYMENT STATUS
    # --------------------------------------------------------

    if staff["employment_status"] != "active":
        return {
            "staff_id": staff_id,
            "airport_code": airport_code,
            "available": False,
            "reason": "Staff member is inactive",
        }

    # --------------------------------------------------------
    # 5. VERIFY ACTIVE AIRPORT ASSIGNMENT
    # --------------------------------------------------------

    airport_assigned = _is_staff_assigned_to_airport(
        staff_id=staff_id,
        airport_code=airport_code,
    )

    if not airport_assigned:
        return {
            "staff_id": staff_id,
            "airport_code": airport_code,
            "available": False,
            "reason": (
                f"Staff member {staff_id} is not actively "
                f"assigned to airport {airport_code}"
            ),
        }

    # --------------------------------------------------------
    # 6. CHECK SCHEDULED SHIFT COVERAGE
    # --------------------------------------------------------

    shifts = get_staff_shifts(staff_id)

    covering_shift = None

    for shift in shifts:
        shift_start = _to_datetime(
            shift["shift_date"],
            shift["start_minute"],
        )

        shift_end = _to_datetime(
            shift["shift_date"],
            shift["end_minute"],
        )

        if (
            shift_start <= request_start
            and request_end <= shift_end
        ):
            covering_shift = shift
            break

    if covering_shift is None:
        return {
            "staff_id": staff_id,
            "airport_code": airport_code,
            "available": False,
            "reason": (
                "No scheduled shift covers the requested time"
            ),
        }

    # --------------------------------------------------------
    # 7. CHECK EXISTING ASSIGNMENT CONFLICTS
    # --------------------------------------------------------

    assignments = get_staff_assignments(staff_id)

    for assignment in assignments:
        assignment_start = _to_datetime(
            assignment["assignment_date"],
            assignment["start_minute"],
        )

        assignment_end = _to_datetime(
            assignment["assignment_date"],
            assignment["end_minute"],
        )

        if _overlaps(
            request_start,
            request_end,
            assignment_start,
            assignment_end,
        ):
            return {
                "staff_id": staff_id,
                "airport_code": airport_code,
                "available": False,
                "reason": (
                    "Staff member has a conflicting assignment"
                ),
                "conflicting_assignment": {
                    "id": assignment["id"],
                    "task_name": assignment["task_name"],
                    "gate_id": assignment["gate_id"],
                    "assignment_date": assignment["assignment_date"],
                },
            }

    # --------------------------------------------------------
    # 8. STAFF IS AVAILABLE
    # --------------------------------------------------------

    return {
        "staff_id": staff_id,
        "airport_code": airport_code,
        "staff_name": staff["full_name"],
        "role": staff["role"],
        "available": True,
        "reason": "Staff member is available",
        "shift_id": covering_shift["id"],
        "requested_date": requested_date,
        "start_time": start_time,
        "end_time": end_time,
    }