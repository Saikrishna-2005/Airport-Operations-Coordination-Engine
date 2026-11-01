from app.database.connection import get_db_connection


def add_staff_airport_constraint():
    conn = get_db_connection()

    try:
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
                idx_staff_one_active_airport
            ON staff_airport_assignments (staff_id)
            WHERE assignment_status = 'active'
            """
        )

        conn.commit()

        print("SUCCESS: Airport assignment constraint created.")
        print("Each staff member can have only one active airport.")

    except Exception as error:
        conn.rollback()
        print("ERROR:", error)

    finally:
        conn.close()


if __name__ == "__main__":
    add_staff_airport_constraint()