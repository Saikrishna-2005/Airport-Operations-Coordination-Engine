from datetime import datetime, timezone

from app.database.connection import get_db_connection


VALID_STATUSES = {
    "AVAILABLE",
    "UNAVAILABLE",
    "UNKNOWN",
}


def initialize_runway_database():
    """
    Create the runway status table.
    """

    connection = get_db_connection()

    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS runway_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                airport_code TEXT NOT NULL,

                runway_code TEXT NOT NULL,

                status TEXT NOT NULL DEFAULT 'UNKNOWN'
                    CHECK (
                        status IN (
                            'AVAILABLE',
                            'UNAVAILABLE',
                            'UNKNOWN'
                        )
                    ),

                reason TEXT,

                updated_by TEXT,

                updated_at TEXT NOT NULL,

                UNIQUE (airport_code, runway_code)
            )
            """
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def update_runway_status(
    airport_code: str,
    runway_code: str,
    status: str,
    updated_by: str,
    reason: str | None = None,
) -> dict:
    """
    Create or update runway availability.

    Status must be entered by an authorized
    operational user or trusted integration.
    """

    airport_code = airport_code.strip().upper()
    runway_code = runway_code.strip().upper()
    status = status.strip().upper()

    if status not in VALID_STATUSES:
        raise ValueError(
            "Invalid runway status."
        )

    if not airport_code or not runway_code:
        raise ValueError(
            "Airport and runway codes are required."
        )

    if not updated_by.strip():
        raise ValueError(
            "Updated-by identifier is required."
        )

    updated_at = datetime.now(
        timezone.utc
    ).isoformat()

    connection = get_db_connection()

    try:
        connection.execute(
            """
            INSERT INTO runway_status (
                airport_code,
                runway_code,
                status,
                reason,
                updated_by,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)

            ON CONFLICT (
                airport_code,
                runway_code
            )

            DO UPDATE SET
                status = excluded.status,
                reason = excluded.reason,
                updated_by = excluded.updated_by,
                updated_at = excluded.updated_at
            """,
            (
                airport_code,
                runway_code,
                status,
                reason,
                updated_by,
                updated_at,
            ),
        )

        connection.commit()

        return get_runway_status(
            airport_code,
            runway_code,
        )

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def get_runway_status(
    airport_code: str,
    runway_code: str,
) -> dict:
    """
    Retrieve runway status.

    Missing records return UNKNOWN,
    never AVAILABLE.
    """

    airport_code = airport_code.strip().upper()
    runway_code = runway_code.strip().upper()

    connection = get_db_connection()

    try:
        row = connection.execute(
            """
            SELECT *
            FROM runway_status
            WHERE airport_code = ?
              AND runway_code = ?
            """,
            (
                airport_code,
                runway_code,
            ),
        ).fetchone()

        if row is None:
            return {
                "airport_code": airport_code,
                "runway_code": runway_code,
                "status": "UNKNOWN",
                "reason": "No runway status recorded.",
                "updated_by": None,
                "updated_at": None,
            }

        return dict(row)

    finally:
        connection.close()


def get_airport_runways(
    airport_code: str,
) -> list[dict]:
    """
    Retrieve all recorded runway statuses
    for an airport.
    """

    airport_code = airport_code.strip().upper()

    connection = get_db_connection()

    try:
        rows = connection.execute(
            """
            SELECT *
            FROM runway_status
            WHERE airport_code = ?
            ORDER BY runway_code
            """,
            (airport_code,),
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:
        connection.close()