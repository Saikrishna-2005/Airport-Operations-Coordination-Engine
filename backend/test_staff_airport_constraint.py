import sqlite3

from app.database.connection import get_db_connection


def test_staff_airport_constraint():
    conn = get_db_connection()

    try:
        conn.execute("BEGIN")

        # Create a temporary test staff member.
        conn.execute(
            """
            INSERT INTO staff_members
                (staff_id, full_name, role, employment_status)
            VALUES (?, ?, ?, ?)
            """,
            (
                "TEST_AIRPORT_CONSTRAINT_001",
                "Constraint Test Staff",
                "Ground Operations",
                "active",
            ),
        )

        # First active airport assignment should succeed.
        conn.execute(
            """
            INSERT INTO staff_airport_assignments
                (staff_id, airport_code, assignment_status)
            VALUES (?, ?, ?)
            """,
            (
                "TEST_AIRPORT_CONSTRAINT_001",
                "HYD",
                "active",
            ),
        )

        print("PASS: First active airport assignment accepted.")

        # Second active airport assignment should fail.
        try:
            conn.execute(
                """
                INSERT INTO staff_airport_assignments
                    (staff_id, airport_code, assignment_status)
                VALUES (?, ?, ?)
                """,
                (
                    "TEST_AIRPORT_CONSTRAINT_001",
                    "DEL",
                    "active",
                ),
            )

            print("FAIL: Multiple active airports were accepted.")

        except sqlite3.IntegrityError:
            print("PASS: Second active airport assignment rejected.")

    except Exception as error:
        print("ERROR:", error)

    finally:
        conn.rollback()
        conn.close()
        print("Test transaction rolled back. No test records saved.")


if __name__ == "__main__":
    test_staff_airport_constraint()