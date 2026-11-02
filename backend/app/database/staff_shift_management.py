from datetime import date, datetime, timedelta

from app.database.connection import get_db_connection


# ============================================================
# TIME HELPERS
# ============================================================

def _to_datetime(day: str, minute: int) -> datetime:
    return datetime.combine(
        date.fromisoformat(day),
        datetime.min.time(),
    ) + timedelta(minutes=minute)


def _overlaps(start_a, end_a, start_b, end_b) -> bool:
    return start_a < end_b and start_b < end_a


def validate_shift(
    shift_date: str,
    start_minute: int,
    end_minute: int,
):
    """
    Validate shift date and minute offsets.

    end_minute > 1440 represents an overnight shift.
    """

    try:
        date.fromisoformat(shift_date)
    except (ValueError, TypeError):
        raise ValueError(
            "Shift date must use YYYY-MM-DD format."
        )

    if type(start_minute) is not int or not 0 <= start_minute <= 1439:
        raise ValueError(
            "Shift start time must be between 00:00 and 23:59."
        )

    if type(end_minute) is not int or not 1 <= end_minute <= 2880:
        raise ValueError(
            "Shift end time must be between 1 and 2880 minutes."
        )

    if end_minute <= start_minute:
        raise ValueError(
            "Shift end time must be after the start time."
        )


# ============================================================
# READ OPERATIONS
# ============================================================

def get_all_staff_shifts(airport_code: str | None = None):
    """
    Retrieve staff shifts.

    If airport_code is provided, return shifts belonging
    only to staff actively assigned to that airport.

    If airport_code is omitted, return all existing shifts.
    """

    if airport_code is not None:
        airport_code = airport_code.strip().upper()

        if (
            len(airport_code) != 3
            or not airport_code.isascii()
            or not airport_code.isalpha()
        ):
            raise ValueError(
                "Airport code must contain exactly 3 English letters"
            )

    connection = get_db_connection()

    try:
        query = """
            SELECT
                ss.id,
                ss.staff_id,
                sm.full_name,
                sm.role,
                ss.shift_date,
                ss.start_minute,
                ss.end_minute
            FROM staff_shifts AS ss
            INNER JOIN staff_members AS sm
                ON ss.staff_id = sm.staff_id
        """

        parameters = []

        if airport_code is not None:
            query += """
                WHERE EXISTS (
                    SELECT 1
                    FROM staff_airport_assignments AS saa
                    WHERE saa.staff_id = ss.staff_id
                      AND saa.airport_code = ?
                      AND saa.assignment_status = 'active'
                )
            """
            parameters.append(airport_code)

        query += """
            ORDER BY
                ss.shift_date DESC,
                ss.start_minute ASC,
                ss.id ASC
        """

        rows = connection.execute(
            query,
            parameters,
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()


def get_shift_by_id(shift_id: int):
    connection = get_db_connection()

    try:
        row = connection.execute(
            """
            SELECT
                id,
                staff_id,
                shift_date,
                start_minute,
                end_minute
            FROM staff_shifts
            WHERE id = ?
            """,
            (shift_id,),
        ).fetchone()

        return dict(row) if row else None

    finally:
        connection.close()


# ============================================================
# INTERNAL VALIDATION
# ============================================================

def _check_shift_overlap(
    connection,
    staff_id: str,
    shift_date: str,
    start_minute: int,
    end_minute: int,
    exclude_shift_id: int | None = None,
):
    """
    Reject overlapping shifts for the same staff member.

    Includes overnight shifts and adjacent dates.
    """

    proposed_start = _to_datetime(shift_date, start_minute)
    proposed_end = _to_datetime(shift_date, end_minute)

    existing_shifts = connection.execute(
        """
        SELECT id, shift_date, start_minute, end_minute
        FROM staff_shifts
        WHERE staff_id = ?
        """,
        (staff_id,),
    ).fetchall()

    for existing in existing_shifts:
        if existing["id"] == exclude_shift_id:
            continue

        existing_start = _to_datetime(
            existing["shift_date"],
            existing["start_minute"],
        )

        existing_end = _to_datetime(
            existing["shift_date"],
            existing["end_minute"],
        )

        if _overlaps(
            proposed_start,
            proposed_end,
            existing_start,
            existing_end,
        ):
            raise ValueError(
                f"Shift overlaps existing shift ID {existing['id']}."
            )


def _check_assignment_coverage(
    connection,
    staff_id: str,
    exclude_shift_id: int | None = None,
    replacement_shift: tuple | None = None,
):
    """
    Ensure all existing assignments remain covered
    after a shift is edited or deleted.

    Other scheduled shifts may provide coverage.
    """

    assignments = connection.execute(
        """
        SELECT
            id,
            assignment_date,
            start_minute,
            end_minute
        FROM staff_assignments
        WHERE staff_id = ?
        """,
        (staff_id,),
    ).fetchall()

    shifts = connection.execute(
        """
        SELECT
            id,
            shift_date,
            start_minute,
            end_minute
        FROM staff_shifts
        WHERE staff_id = ?
        """,
        (staff_id,),
    ).fetchall()

    available_shifts = [
        (
            shift["shift_date"],
            shift["start_minute"],
            shift["end_minute"],
        )
        for shift in shifts
        if shift["id"] != exclude_shift_id
    ]

    if replacement_shift is not None:
        available_shifts.append(replacement_shift)

    for assignment in assignments:
        assignment_start = _to_datetime(
            assignment["assignment_date"],
            assignment["start_minute"],
        )

        assignment_end = _to_datetime(
            assignment["assignment_date"],
            assignment["end_minute"],
        )

        covered = any(
            _to_datetime(day, start) <= assignment_start
            and assignment_end <= _to_datetime(day, end)
            for day, start, end in available_shifts
        )

        if not covered:
            raise ValueError(
                "Shift modification would leave existing "
                f"assignment ID {assignment['id']} "
                "without scheduled shift coverage."
            )


# ============================================================
# CREATE SHIFT
# ============================================================

def create_staff_shift(
    staff_id: str,
    shift_date: str,
    start_minute: int,
    end_minute: int,
):
    validate_shift(shift_date, start_minute, end_minute)

    connection = get_db_connection()

    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("BEGIN IMMEDIATE")

        staff = connection.execute(
            """
            SELECT staff_id
            FROM staff_members
            WHERE staff_id = ?
            """,
            (staff_id,),
        ).fetchone()

        if staff is None:
            raise ValueError("Staff member not found.")

        _check_shift_overlap(
            connection,
            staff_id,
            shift_date,
            start_minute,
            end_minute,
        )

        cursor = connection.execute(
            """
            INSERT INTO staff_shifts (
                staff_id,
                shift_date,
                start_minute,
                end_minute
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                staff_id,
                shift_date,
                start_minute,
                end_minute,
            ),
        )

        shift_id = cursor.lastrowid
        connection.commit()

        return get_shift_by_id(shift_id)

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


# ============================================================
# UPDATE SHIFT
# ============================================================

def update_staff_shift(
    shift_id: int,
    shift_date: str,
    start_minute: int,
    end_minute: int,
):
    validate_shift(shift_date, start_minute, end_minute)

    connection = get_db_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")

        existing = connection.execute(
            """
            SELECT id, staff_id
            FROM staff_shifts
            WHERE id = ?
            """,
            (shift_id,),
        ).fetchone()

        if existing is None:
            connection.rollback()
            return None

        staff_id = existing["staff_id"]

        _check_shift_overlap(
            connection,
            staff_id,
            shift_date,
            start_minute,
            end_minute,
            exclude_shift_id=shift_id,
        )

        _check_assignment_coverage(
            connection,
            staff_id,
            exclude_shift_id=shift_id,
            replacement_shift=(
                shift_date,
                start_minute,
                end_minute,
            ),
        )

        connection.execute(
            """
            UPDATE staff_shifts
            SET
                shift_date = ?,
                start_minute = ?,
                end_minute = ?
            WHERE id = ?
            """,
            (
                shift_date,
                start_minute,
                end_minute,
                shift_id,
            ),
        )

        connection.commit()

        return get_shift_by_id(shift_id)

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


# ============================================================
# DELETE SHIFT
# ============================================================

def delete_staff_shift(shift_id: int):
    connection = get_db_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")

        existing = connection.execute(
            """
            SELECT id, staff_id
            FROM staff_shifts
            WHERE id = ?
            """,
            (shift_id,),
        ).fetchone()

        if existing is None:
            connection.rollback()
            return False

        _check_assignment_coverage(
            connection,
            existing["staff_id"],
            exclude_shift_id=shift_id,
        )

        connection.execute(
            """
            DELETE FROM staff_shifts
            WHERE id = ?
            """,
            (shift_id,),
        )

        connection.commit()
        return True

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()