import sqlite3
from pathlib import Path


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

DB_PATH = BASE_DIR / "data" / "airport_operations.db"


# ============================================================
# GET STAFF MEMBERS BY AIRPORT
# ============================================================

def get_airport_staff(airport_code: str):

    airport_code = airport_code.strip().upper()

    if (
        len(airport_code) != 3
        or not airport_code.isascii()
        or not airport_code.isalpha()
    ):
        return {
            "success": False,
            "error": "Invalid airport code",
        }

    if not DB_PATH.is_file():
        return {
            "success": False,
            "error": "Database file not found",
        }

    connection = sqlite3.connect(
        DB_PATH.as_uri() + "?mode=ro",
        uri=True,
    )

    connection.row_factory = sqlite3.Row

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                sm.staff_id,
                sm.full_name,
                sm.role,
                sm.employment_status,
                saa.airport_code,
                saa.assignment_status

            FROM staff_members AS sm

            INNER JOIN staff_airport_assignments AS saa
                ON sm.staff_id = saa.staff_id

            WHERE saa.airport_code = ?
              AND saa.assignment_status = 'active'
              AND sm.employment_status = 'active'

            ORDER BY sm.full_name ASC
            """,
            (airport_code,),
        )

        records = cursor.fetchall()

        staff_list = [
            {
                "staff_id": row["staff_id"],
                "full_name": row["full_name"],
                "role": row["role"],
                "employment_status": row["employment_status"],
                "airport_code": row["airport_code"],
                "assignment_status": row["assignment_status"],
            }
            for row in records
        ]

        return {
            "success": True,
            "airport_code": airport_code,
            "total_staff": len(staff_list),
            "staff": staff_list,
        }

    finally:
        connection.close()


# ============================================================
# MANUAL TEST
# ============================================================

if __name__ == "__main__":

    result = get_airport_staff("HYD")

    print("\nAIRPORT STAFF RESULT")
    print("--------------------")

    print(result)