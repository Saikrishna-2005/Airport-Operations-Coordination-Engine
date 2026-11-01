import sqlite3

from app.database.connection import get_db_connection
from app.tools.airport_lookup import lookup_airport


# --------------------------------------------------
# 1. CREATE AIRPORT MONITORING TABLE
# --------------------------------------------------

def create_airport_monitoring_table():
    """Create the monitored_airports table if missing."""

    connection = get_db_connection()

    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS monitored_airports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                airport_code TEXT NOT NULL UNIQUE,
                added_by TEXT NOT NULL,
                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                CHECK (length(airport_code) = 3)
            )
        """)

        connection.commit()

        return {
            "success": True,
            "message": "Airport monitoring table is ready."
        }

    except sqlite3.Error:
        connection.rollback()
        raise

    finally:
        connection.close()


# --------------------------------------------------
# 2. ADD AIRPORT
# --------------------------------------------------

def add_monitored_airport(
    airport_code: str,
    added_by: str
) -> dict:
    """Validate and save an airport to the monitoring list."""

    airport = lookup_airport(airport_code)

    if not airport["success"]:
        return {
            "success": False,
            "reason": airport["reason"]
        }

    code = airport["airport_code"]

    if not isinstance(added_by, str) or not added_by.strip():
        return {
            "success": False,
            "reason": "A valid user identifier is required."
        }

    connection = get_db_connection()

    try:
        connection.execute("""
            INSERT INTO monitored_airports (
                airport_code,
                added_by
            )
            VALUES (?, ?)
        """, (code, added_by.strip()))

        connection.commit()

        return {
            "success": True,
            "message": f"Airport {code} added successfully.",
            "airport": airport
        }

    except sqlite3.IntegrityError:
        connection.rollback()

        return {
            "success": False,
            "reason": f"Airport {code} is already monitored."
        }

    finally:
        connection.close()


# --------------------------------------------------
# 3. LIST MONITORED AIRPORTS
# --------------------------------------------------

def list_monitored_airports() -> dict:
    """Return all airports saved in the monitoring list."""

    connection = get_db_connection()

    try:
        cursor = connection.execute("""
            SELECT
                id,
                airport_code,
                added_by,
                created_at
            FROM monitored_airports
            ORDER BY id ASC
        """)

        rows = cursor.fetchall()

        airports = []

        for row in rows:
            airport = lookup_airport(row["airport_code"])

            airports.append({
                "id": row["id"],
                "airport_code": row["airport_code"],
                "added_by": row["added_by"],
                "created_at": row["created_at"],
                "airport_name": airport.get("name"),
                "city": airport.get("city"),
                "country": airport.get("country"),
                "latitude": airport.get("latitude"),
                "longitude": airport.get("longitude")
            })

        return {
            "success": True,
            "count": len(airports),
            "airports": airports
        }

    finally:
        connection.close()


# --------------------------------------------------
# 4. REMOVE AIRPORT
# --------------------------------------------------

def remove_monitored_airport(airport_code: str) -> dict:
    """Remove an airport from the monitoring list."""

    if not isinstance(airport_code, str):
        return {
            "success": False,
            "reason": "Invalid airport code."
        }

    code = airport_code.strip().upper()

    connection = get_db_connection()

    try:
        cursor = connection.execute("""
            DELETE FROM monitored_airports
            WHERE airport_code = ?
        """, (code,))

        connection.commit()

        if cursor.rowcount == 0:
            return {
                "success": False,
                "reason": f"Airport {code} is not monitored."
            }

        return {
            "success": True,
            "message": f"Airport {code} removed successfully."
        }

    finally:
        connection.close()