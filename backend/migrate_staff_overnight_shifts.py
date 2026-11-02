import sqlite3

from app.database.connection import get_db_connection


def migrate_staff_shifts():
    connection = get_db_connection()

    try:
        # Check whether the migration has already been applied.
        row = connection.execute(
            """
            SELECT sql
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'staff_shifts'
            """
        ).fetchone()

        if row is None:
            raise RuntimeError(
                "staff_shifts table does not exist"
            )

        existing_schema = row["sql"]

        if "BETWEEN 1 AND 2880" in existing_schema:
            print("Migration already applied.")
            return

        # Confirm that no shift records exist.
        count = connection.execute(
            "SELECT COUNT(*) FROM staff_shifts"
        ).fetchone()[0]

        if count != 0:
            raise RuntimeError(
                "Migration stopped: staff_shifts contains records."
            )

        # Confirm that no staff assignments exist.
        assignment_count = connection.execute(
            "SELECT COUNT(*) FROM staff_assignments"
        ).fetchone()[0]

        if assignment_count != 0:
            raise RuntimeError(
                "Migration stopped: staff_assignments contains records."
            )

        connection.execute("BEGIN IMMEDIATE")

        # The existing table is empty, so it can be
        # rebuilt without copying records.
        connection.execute(
            "DROP TABLE staff_shifts"
        )

        connection.execute(
            """
            CREATE TABLE staff_shifts (
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

        connection.commit()

        print("Staff overnight shift migration successful.")

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    migrate_staff_shifts()