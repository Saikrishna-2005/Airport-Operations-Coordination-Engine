from datetime import date, timedelta

from app.database.connection import get_db_connection


def allocate_staff(
    staff_id: str,
    assignment_date: str,
    start_time: str,
    end_time: str,
    task_name: str,
    gate_id: str | None = None,
    airport_code: str | None = None,
):
    """
    Allocate staff to an operational task.

    Supports same-day assignments only.

    Availability validation and assignment insertion occur
    within the same SQLite write transaction to prevent
    concurrent allocation conflicts.

    Airport codes are stored permanently with assignments
    to preserve historical airport information.
    """

    # ============================================================
    # STEP 1 - VALIDATE ASSIGNMENT DATE
    # ============================================================

    try:
        date.fromisoformat(assignment_date)
    except ValueError:
        return {
            "success": False,
            "reason": "Invalid assignment date",
        }

    # ============================================================
    # STEP 2 - CONVERT TIME TO MINUTES
    # ============================================================

    def to_minutes(value):
        parts = value.split(":")

        if len(parts) != 2:
            raise ValueError("Invalid time format")

        hours, minutes = map(int, parts)

        if not (0 <= hours <= 23 and 0 <= minutes <= 59):
            raise ValueError("Invalid time value")

        return hours * 60 + minutes

    try:
        start_minute = to_minutes(start_time)
        end_minute = to_minutes(end_time)

    except (ValueError, TypeError):
        return {
            "success": False,
            "reason": "Time must use HH:MM format",
        }

    # ============================================================
    # STEP 3 - VALIDATE SAME-DAY ASSIGNMENT
    # ============================================================

    if end_minute <= start_minute:
        return {
            "success": False,
            "reason": (
                "Staff allocation currently supports "
                "same-day intervals only"
            ),
        }

    # ============================================================
    # STEP 4 - NORMALIZE INPUT VALUES
    # ============================================================

    staff_id = staff_id.strip()
    task_name = task_name.strip()

    gate_id = gate_id.strip() if gate_id else None

    airport_code = (airport_code or "").strip().upper()

    # ============================================================
    # STEP 5 - VALIDATE REQUIRED FIELDS
    # ============================================================

    if not airport_code:
        return {
            "success": False,
            "reason": "Airport code is required for staff allocation",
        }

    if not staff_id or not task_name:
        return {
            "success": False,
            "reason": "Staff ID and task name are required",
        }

    # ============================================================
    # STEP 6 - CONNECT TO SQLITE DATABASE
    # ============================================================

    conn = get_db_connection()

    try:
        # Acquire a write lock before checking availability.
        # This prevents concurrent requests from creating
        # overlapping assignments.

        conn.execute("BEGIN IMMEDIATE")

        # ========================================================
        # STEP 7 - VERIFY STAFF MEMBER EXISTS
        # ========================================================

        staff = conn.execute(
            """
            SELECT
                staff_id,
                employment_status
            FROM staff_members
            WHERE staff_id = ?
            """,
            (staff_id,),
        ).fetchone()

        if staff is None:
            conn.rollback()

            return {
                "success": False,
                "reason": "Staff member not found",
            }

        # ========================================================
        # STEP 8 - VERIFY STAFF IS ACTIVE
        # ========================================================

        if staff["employment_status"] != "active":
            conn.rollback()

            return {
                "success": False,
                "reason": "Staff member is inactive",
            }

        # ========================================================
        # STEP 9 - VERIFY AIRPORT ASSIGNMENT
        # ========================================================

        airport_assignment = conn.execute(
            """
            SELECT id
            FROM staff_airport_assignments
            WHERE staff_id = ?
              AND airport_code = ?
              AND assignment_status = 'active'
            LIMIT 1
            """,
            (
                staff_id,
                airport_code,
            ),
        ).fetchone()

        if airport_assignment is None:
            conn.rollback()

            return {
                "success": False,
                "reason": (
                    f"Staff member {staff_id} is not actively "
                    f"assigned to airport {airport_code}"
                ),
            }

        # ========================================================
        # STEP 10 - PREPARE SHIFT VALIDATION
        # ========================================================

        requested_day = date.fromisoformat(assignment_date)

        previous_day = (
            requested_day - timedelta(days=1)
        ).isoformat()

        # ========================================================
        # STEP 11 - FETCH STAFF SHIFTS
        # ========================================================

        shifts = conn.execute(
            """
            SELECT
                shift_date,
                start_minute,
                end_minute
            FROM staff_shifts
            WHERE staff_id = ?
              AND shift_date IN (?, ?)
            """,
            (
                staff_id,
                assignment_date,
                previous_day,
            ),
        ).fetchall()

        # ========================================================
        # STEP 12 - CHECK SHIFT COVERAGE
        # ========================================================

        shift_covers_request = False

        for shift in shifts:

            offset = (
                0
                if shift["shift_date"] == assignment_date
                else -1440
            )

            shift_start = shift["start_minute"] + offset

            shift_end = shift["end_minute"] + offset

            if (
                shift_start <= start_minute
                and shift_end >= end_minute
            ):
                shift_covers_request = True
                break

        if not shift_covers_request:
            conn.rollback()

            return {
                "success": False,
                "reason": (
                    "Requested time is outside "
                    "the assigned staff shift"
                ),
            }

        # ========================================================
        # STEP 13 - CHECK OVERLAPPING ASSIGNMENTS
        # ========================================================

        # Overlap condition:
        #
        # existing_start < requested_end
        # AND
        # existing_end > requested_start

        conflict = conn.execute(
            """
            SELECT
                id,
                task_name,
                gate_id
            FROM staff_assignments
            WHERE staff_id = ?
              AND assignment_date = ?
              AND start_minute < ?
              AND end_minute > ?
            LIMIT 1
            """,
            (
                staff_id,
                assignment_date,
                end_minute,
                start_minute,
            ),
        ).fetchone()

        if conflict is not None:
            conn.rollback()

            return {
                "success": False,
                "reason": (
                    "Staff member already has "
                    "an overlapping assignment"
                ),
                "conflicting_assignment_id": conflict["id"],
            }

        # ========================================================
        # STEP 14 - INSERT STAFF ASSIGNMENT
        # ========================================================

        # IMPORTANT UPDATE:
        #
        # airport_code is now stored directly in the
        # staff_assignments table.
        #
        # This preserves the original airport even when
        # a staff member is transferred later.

        cursor = conn.execute(
            """
            INSERT INTO staff_assignments
            (
                staff_id,
                airport_code,
                assignment_date,
                gate_id,
                task_name,
                start_minute,
                end_minute
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                staff_id,
                airport_code,
                assignment_date,
                gate_id,
                task_name,
                start_minute,
                end_minute,
            ),
        )

        # ========================================================
        # STEP 15 - GET NEW ASSIGNMENT ID
        # ========================================================

        assignment_id = cursor.lastrowid

        # ========================================================
        # STEP 16 - COMMIT TRANSACTION
        # ========================================================

        conn.commit()

        # ========================================================
        # STEP 17 - RETURN SUCCESS RESPONSE
        # ========================================================

        return {
            "success": True,
            "assignment_id": assignment_id,
            "staff_id": staff_id,
            "airport_code": airport_code,
            "assignment_date": assignment_date,
            "start_time": start_time,
            "end_time": end_time,
            "task_name": task_name,
            "gate_id": gate_id,
            "message": "Staff allocated successfully",
        }

    # ============================================================
    # STEP 18 - ROLLBACK ON ERROR
    # ============================================================

    except Exception:
        conn.rollback()
        raise

    # ============================================================
    # STEP 19 - CLOSE DATABASE CONNECTION
    # ============================================================

    finally:
        conn.close()