import sqlite3

from app.database.connection import get_db_connection
from app.database.staff_shift_management import validate_shift
from app.tools.airport_lookup import lookup_airport

# ============================================================
# GET ALL STAFF MEMBERS
# ============================================================

def get_all_staff(airport_code: str | None = None):
    """Return all staff, or staff assigned actively to a specified airport.

    Staff without active airport assignments remain visible when unfiltered.
    """
    if airport_code is not None:
        airport_code = airport_code.strip().upper()
        if (
            len(airport_code) != 3
            or not airport_code.isascii()
            or not airport_code.isalpha()
        ):
            raise ValueError("Airport code must contain exactly 3 English letters")

    connection = get_db_connection()
    try:
        query = """
            SELECT
                sm.staff_id,
                sm.full_name,
                sm.role,
                sm.employment_status,
                sm.created_at,
                saa.airport_code
            FROM staff_members AS sm
            LEFT JOIN staff_airport_assignments AS saa
                ON sm.staff_id = saa.staff_id
                AND saa.assignment_status = 'active'
        """
        parameters = []
        if airport_code is not None:
            query += " WHERE saa.airport_code = ?"
            parameters.append(airport_code)

        query += " ORDER BY sm.created_at DESC, sm.staff_id"
        rows = connection.execute(query, parameters).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


# ============================================================
# GET STAFF MEMBER BY ID
# ============================================================

def get_staff_by_id(staff_id: str):
    """
    Retrieve a staff member using their Staff ID.
    """

    connection = get_db_connection()

    try:
        row = connection.execute(
            """
            SELECT
                staff_id,
                full_name,
                role,
                employment_status,
                created_at
            FROM staff_members
            WHERE staff_id = ?
            """,
            (staff_id,),
        ).fetchone()

        return dict(row) if row else None

    finally:
        connection.close()


# ============================================================
# ADD STAFF MEMBER WITH MANDATORY SHIFT
# ============================================================

def create_staff_member(
    staff_id: str,
    full_name: str,
    role: str,
    employment_status: str,
    shift_date: str,
    start_minute: int,
    end_minute: int,
    airport_code: str,
):
    """
    Create a staff member and assign their initial shift.

    Both operations execute within one SQLite transaction.

    If staff creation or shift creation fails,
    the entire transaction is rolled back.

    Overnight shifts are supported using end_minute > 1440.
    """

    # --------------------------------------------------------
    # STEP 1: VALIDATE STAFF DETAILS
    # --------------------------------------------------------

    staff_id = staff_id.strip()
    full_name = full_name.strip()
    role = role.strip()
    employment_status = employment_status.strip().lower()

    if not staff_id:
        return {
            "success": False,
            "reason": "Staff ID cannot be empty",
        }

    if not full_name:
        return {
            "success": False,
            "reason": "Staff name cannot be empty",
        }

    if not role:
        return {
            "success": False,
            "reason": "Staff role cannot be empty",
        }

    if employment_status not in {"active", "inactive"}:
        return {
            "success": False,
            "reason": (
                "Employment status must be active or inactive"
            ),
        }

    # --------------------------------------------------------
    # VALIDATE AIRPORT ASSIGNMENT
    # --------------------------------------------------------

    airport_result = lookup_airport(airport_code)

    if not airport_result["success"]:
        return {
            "success": False,
            "reason": airport_result["reason"],
        }

    airport_code = airport_result["airport_code"]

    # --------------------------------------------------------
    # STEP 2: VALIDATE SHIFT DETAILS
    # --------------------------------------------------------

    validate_shift(
        shift_date=shift_date,
        start_minute=start_minute,
        end_minute=end_minute,
    )

    # --------------------------------------------------------
    # STEP 3: OPEN DATABASE CONNECTION
    # --------------------------------------------------------

    connection = get_db_connection()

    try:
        connection.execute("PRAGMA foreign_keys = ON")

        # Prevent concurrent writes from bypassing checks.
        connection.execute("BEGIN IMMEDIATE")

        # ----------------------------------------------------
        # STEP 4: CHECK DUPLICATE STAFF ID
        # ----------------------------------------------------

        existing_staff = connection.execute(
            """
            SELECT staff_id
            FROM staff_members
            WHERE staff_id = ?
            """,
            (staff_id,),
        ).fetchone()

        if existing_staff is not None:
            connection.rollback()

            return {
                "success": False,
                "reason": "Staff ID already exists",
            }

        # ----------------------------------------------------
        # STEP 5: CREATE STAFF MEMBER
        # ----------------------------------------------------

        connection.execute(
            """
            INSERT INTO staff_members (
                staff_id,
                full_name,
                role,
                employment_status
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                staff_id,
                full_name,
                role,
                employment_status,
            ),
        )

        # ----------------------------------------------------
        # CREATE STAFF AIRPORT ASSIGNMENT
        # ----------------------------------------------------

        connection.execute(
            """
            INSERT INTO staff_airport_assignments (
                staff_id,
                airport_code,
                assignment_status
            )
            VALUES (?, ?, 'active')
            """,
            (
                staff_id,
                airport_code,
            ),
        )

        # ----------------------------------------------------
        # STEP 6: CREATE INITIAL STAFF SHIFT
        # ----------------------------------------------------

        shift_cursor = connection.execute(
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

        shift_id = shift_cursor.lastrowid

        # ----------------------------------------------------
        # STEP 7: COMMIT BOTH OPERATIONS
        # ----------------------------------------------------

        connection.commit()

        return {
            "success": True,
            "message": (
                "Staff member, airport assignment, "
                "and initial shift created successfully"
            ),
            "staff_id": staff_id,
            "airport_code": airport_code,
            "shift": {
                "id": shift_id,
                "shift_date": shift_date,
                "start_minute": start_minute,
                "end_minute": end_minute,
            },
        }

    # --------------------------------------------------------
    # HANDLE SQLITE INTEGRITY ERRORS
    # --------------------------------------------------------

    except sqlite3.IntegrityError as error:
        connection.rollback()

        error_message = str(error)

        if "staff_members.staff_id" in error_message:
            return {
                "success": False,
                "reason": "Staff ID already exists",
            }

        if (
            "idx_staff_one_active_airport" in error_message
            or "UNIQUE constraint failed: staff_airport_assignments.staff_id" in error_message
        ):
            return {
                "success": False,
                "reason": (
                    "Staff member is already actively assigned "
                    "to another airport"
                ),
            }

        if (
            "UNIQUE constraint failed: "
            "staff_airport_assignments.staff_id, "
            "staff_airport_assignments.airport_code"
        ) in error_message:
            return {
                "success": False,
                "reason": "Staff member already has an assignment for this airport",
            }

        raise

    # --------------------------------------------------------
    # HANDLE OTHER ERRORS
    # --------------------------------------------------------

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


# ============================================================
# UPDATE STAFF MEMBER
# ============================================================

def update_staff_member(
    staff_id: str,
    full_name: str,
    role: str,
    employment_status: str,
):
    """
    Update staff member details.

    Staff ID cannot be modified.

    Shift editing is handled separately by
    staff_shift_management.py.
    """

    connection = get_db_connection()

    try:
        cursor = connection.execute(
            """
            UPDATE staff_members
            SET
                full_name = ?,
                role = ?,
                employment_status = ?
            WHERE staff_id = ?
            """,
            (
                full_name,
                role,
                employment_status,
                staff_id,
            ),
        )

        connection.commit()

        if cursor.rowcount == 0:
            return {
                "success": False,
                "reason": "Staff member not found",
            }

        return {
            "success": True,
            "message": "Staff member updated successfully",
            "staff_id": staff_id,
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


# ============================================================
# DELETE STAFF MEMBER
# ============================================================

def delete_staff_member(staff_id: str):
    """
    Delete a staff member only when no related
    assignments or shifts exist.

    Existing staff assignments and shifts must
    never be silently deleted.
    """

    connection = get_db_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")

        # ----------------------------------------------------
        # CHECK STAFF EXISTENCE
        # ----------------------------------------------------

        staff = connection.execute(
            """
            SELECT staff_id
            FROM staff_members
            WHERE staff_id = ?
            """,
            (staff_id,),
        ).fetchone()

        if staff is None:
            connection.rollback()

            return {
                "success": False,
                "reason": "Staff member not found",
            }

        # ----------------------------------------------------
        # CHECK RELATED DATABASE RECORDS
        # ----------------------------------------------------

        related_tables = [
            "staff_assignments",
            "staff_airport_assignments",
            "staff_shifts",
        ]

        for table in related_tables:
            table_exists = connection.execute(
                """
                SELECT 1
                FROM sqlite_master
                WHERE type = 'table'
                  AND name = ?
                """,
                (table,),
            ).fetchone()

            if not table_exists:
                continue

            related_record = connection.execute(
                f"""
                SELECT 1
                FROM {table}
                WHERE staff_id = ?
                LIMIT 1
                """,
                (staff_id,),
            ).fetchone()

            if related_record is not None:
                connection.rollback()

                return {
                    "success": False,
                    "reason": (
                        "Cannot delete staff member with "
                        "existing assignments or shifts"
                    ),
                }

        # ----------------------------------------------------
        # DELETE STAFF MEMBER
        # ----------------------------------------------------

        connection.execute(
            """
            DELETE FROM staff_members
            WHERE staff_id = ?
            """,
            (staff_id,),
        )

        connection.commit()

        return {
            "success": True,
            "message": "Staff member deleted successfully",
            "staff_id": staff_id,
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()