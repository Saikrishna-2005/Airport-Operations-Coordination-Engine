from app.database.connection import get_db_connection
from app.logger import logger


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def minutes_to_time(minutes: int) -> str:
    """
    Convert minutes into HH:MM format.

    Examples:
        540  -> 09:00
        1020 -> 17:00
        1500 -> 01:00
    """

    hours = (minutes // 60) % 24
    remaining_minutes = minutes % 60

    return f"{hours:02d}:{remaining_minutes:02d}"


# ============================================================
# INITIALIZE STAFF DATABASE TABLES
# ============================================================

def initialize_staff_tables():
    """
    Create staff-related tables without changing
    existing airport operations tables.

    Existing staff records and assignments are preserved.
    """

    connection = get_db_connection()

    try:
        connection.execute("PRAGMA foreign_keys = ON")

        # ----------------------------------------------------
        # STAFF MEMBERS
        # ----------------------------------------------------

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS staff_members (
                staff_id TEXT PRIMARY KEY,

                full_name TEXT NOT NULL,

                role TEXT NOT NULL,

                employment_status TEXT NOT NULL
                    DEFAULT 'active'
                    CHECK (
                        employment_status IN (
                            'active',
                            'inactive'
                        )
                    ),

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # ----------------------------------------------------
        # STAFF SHIFTS
        # ----------------------------------------------------

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS staff_shifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                staff_id TEXT NOT NULL,

                shift_date TEXT NOT NULL,

                start_minute INTEGER NOT NULL
                    CHECK (
                        start_minute BETWEEN 0 AND 1439
                    ),

                end_minute INTEGER NOT NULL
                    CHECK (
                        end_minute BETWEEN 1 AND 2880
                    ),

                FOREIGN KEY (staff_id)
                    REFERENCES staff_members(staff_id),

                CHECK (
                    end_minute > start_minute
                )
            )
            """
        )

        # ----------------------------------------------------
        # STAFF ASSIGNMENTS
        # ----------------------------------------------------

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS staff_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                staff_id TEXT NOT NULL,

                airport_code TEXT,

                assignment_date TEXT NOT NULL,

                gate_id TEXT,

                task_name TEXT NOT NULL,

                start_minute INTEGER NOT NULL
                    CHECK (
                        start_minute BETWEEN 0 AND 1439
                    ),

                end_minute INTEGER NOT NULL
                    CHECK (
                        end_minute BETWEEN 1 AND 1440
                    ),

                FOREIGN KEY (staff_id)
                    REFERENCES staff_members(staff_id),

                CHECK (
                    end_minute > start_minute
                )
            )
            """
        )

        # ----------------------------------------------------
        # VERIFY AIRPORT CODE COLUMN EXISTS
        # ----------------------------------------------------

        columns = connection.execute(
            "PRAGMA table_info(staff_assignments)"
        ).fetchall()

        column_names = {
            column["name"]
            for column in columns
        }

        if "airport_code" not in column_names:
            connection.execute(
                """
                ALTER TABLE staff_assignments
                ADD COLUMN airport_code TEXT
                """
            )

            logger.info(
                "Added airport_code column to staff_assignments"
            )

        connection.commit()

        logger.info(
            "Staff database tables initialized successfully"
        )

    except Exception:
        connection.rollback()

        logger.exception(
            "Failed to initialize staff database tables"
        )

        raise

    finally:
        connection.close()


# ============================================================
# STAFF DATABASE READ OPERATIONS
# ============================================================

def get_staff_member(staff_id: str) -> dict | None:
    """
    Retrieve a staff member by staff ID.
    """

    connection = get_db_connection()

    try:
        row = connection.execute(
            """
            SELECT
                staff_id,
                full_name,
                role,
                employment_status
            FROM staff_members
            WHERE staff_id = ?
            """,
            (staff_id,),
        ).fetchone()

        return dict(row) if row is not None else None

    finally:
        connection.close()


# ============================================================
# GET STAFF SHIFTS
# ============================================================

def get_staff_shifts(staff_id: str) -> list[dict]:
    """
    Retrieve scheduled shifts for a staff member.

    end_minute may exceed 1440 for overnight shifts.
    """

    connection = get_db_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                id,
                staff_id,
                shift_date,
                start_minute,
                end_minute
            FROM staff_shifts
            WHERE staff_id = ?
            ORDER BY shift_date, start_minute
            """,
            (staff_id,),
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()


# ============================================================
# GET STAFF ASSIGNMENTS
# ============================================================

def get_staff_assignments(staff_id: str) -> list[dict]:
    """
    Retrieve existing assignments for a staff member.

    This function remains compatible with the existing
    staff availability checker.
    """

    connection = get_db_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                id,
                staff_id,
                assignment_date,
                gate_id,
                task_name,
                start_minute,
                end_minute
            FROM staff_assignments
            WHERE staff_id = ?
            ORDER BY assignment_date, start_minute
            """,
            (staff_id,),
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()


# ============================================================
# AIRPORT-SPECIFIC STAFF ASSIGNMENT HISTORY
# ============================================================

def get_staff_assignment_history(
    airport_code: str | None = None,
    staff_id: str | None = None,
    include_unknown: bool = False,
) -> list[dict]:
    """
    Retrieve staff assignment history.

    Features:
        - Filter by airport code.
        - Optionally filter by staff ID.
        - Include readable assignment times.
        - Preserve historical records with unknown airports.

    Rules:
        - If airport_code is provided, only records belonging
          to that airport are returned.
        - If include_unknown=True and no airport is selected,
          records with NULL airport_code are returned.
        - If no filters are provided, all assignments with
          known airports are returned.

    This function performs read-only database operations.
    """

    connection = get_db_connection()

    try:
        query = """
            SELECT
                sa.id,
                sa.staff_id,
                sm.full_name,
                sm.role,
                sa.airport_code,
                sa.assignment_date,
                sa.gate_id,
                sa.task_name,
                sa.start_minute,
                sa.end_minute
            FROM staff_assignments AS sa
            LEFT JOIN staff_members AS sm
                ON sa.staff_id = sm.staff_id
        """

        conditions = []
        parameters = []

        # ----------------------------------------------------
        # FILTER BY AIRPORT
        # ----------------------------------------------------

        if airport_code:
            normalized_airport = airport_code.strip().upper()

            conditions.append(
                "sa.airport_code = ?"
            )

            parameters.append(normalized_airport)

        elif include_unknown:
            conditions.append(
                "sa.airport_code IS NULL"
            )

        else:
            conditions.append(
                "sa.airport_code IS NOT NULL"
            )

        # ----------------------------------------------------
        # OPTIONAL STAFF FILTER
        # ----------------------------------------------------

        if staff_id:
            conditions.append(
                "sa.staff_id = ?"
            )

            parameters.append(staff_id.strip())

        # ----------------------------------------------------
        # BUILD WHERE CLAUSE
        # ----------------------------------------------------

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        # ----------------------------------------------------
        # ORDER RESULTS
        # ----------------------------------------------------

        query += """
            ORDER BY
                sa.assignment_date DESC,
                sa.start_minute DESC,
                sa.id DESC
        """

        rows = connection.execute(
            query,
            tuple(parameters),
        ).fetchall()

        # ----------------------------------------------------
        # FORMAT RESULTS
        # ----------------------------------------------------

        assignments = []

        for row in rows:
            assignment = dict(row)

            assignment["start_time"] = minutes_to_time(
                assignment["start_minute"]
            )

            assignment["end_time"] = minutes_to_time(
                assignment["end_minute"]
            )

            assignments.append(assignment)

        return assignments

    finally:
        connection.close()