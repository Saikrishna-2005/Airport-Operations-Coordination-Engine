from app.database.connection import get_db_connection


def check_staff_airports():
    conn = get_db_connection()

    try:
        rows = conn.execute(
            """
            SELECT
                staff_id,
                COUNT(*) AS active_airports
            FROM staff_airport_assignments
            WHERE assignment_status = 'active'
            GROUP BY staff_id
            HAVING COUNT(*) > 1
            """
        ).fetchall()

        for row in rows:
            print(dict(row))

        print("Staff with multiple active airports:", len(rows))

    finally:
        conn.close()


if __name__ == "__main__":
    check_staff_airports()