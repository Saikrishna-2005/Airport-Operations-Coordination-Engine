import sqlite3
from pathlib import Path


# --------------------------------------------------
# DATABASE LOCATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[1]

DB_PATH = BASE_DIR / "data" / "airport_operations.db"


# --------------------------------------------------
# DATABASE MIGRATION
# --------------------------------------------------

def migrate_database():

    if not DB_PATH.is_file():
        raise FileNotFoundError(
            f"SQLite database not found: {DB_PATH}"
        )

    connection = sqlite3.connect(DB_PATH)

    try:
        connection.execute("PRAGMA foreign_keys = ON")

        cursor = connection.cursor()

        # ------------------------------------------
        # 1. CREATE STAFF AIRPORT ASSIGNMENTS TABLE
        # ------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS staff_airport_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                staff_id TEXT NOT NULL,

                airport_code TEXT NOT NULL
                    CHECK (
                        length(airport_code) = 3
                        AND airport_code = upper(airport_code)
                    ),

                assignment_status TEXT NOT NULL
                    DEFAULT 'active'
                    CHECK (
                        assignment_status IN (
                            'active',
                            'inactive'
                        )
                    ),

                assigned_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (staff_id)
                    REFERENCES staff_members(staff_id),

                UNIQUE (staff_id, airport_code)
            )
        """)

        print(
            "SUCCESS: staff_airport_assignments table ready."
        )

        # ------------------------------------------
        # 2. ADD AIRPORT CODE TO STAFF ASSIGNMENTS
        # ------------------------------------------

        cursor.execute(
            "PRAGMA table_info(staff_assignments)"
        )

        existing_columns = [
            row[1]
            for row in cursor.fetchall()
        ]

        if "airport_code" not in existing_columns:

            cursor.execute("""
                ALTER TABLE staff_assignments
                ADD COLUMN airport_code TEXT
            """)

            print(
                "SUCCESS: airport_code added to staff_assignments."
            )

        else:
            print(
                "INFO: airport_code already exists in staff_assignments."
            )

        # ------------------------------------------
        # 3. CREATE INDEXES
        # ------------------------------------------

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS
                idx_staff_airport_code
            ON staff_airport_assignments(airport_code)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS
                idx_staff_assignment_airport
            ON staff_assignments(airport_code)
        """)

        # ------------------------------------------
        # 4. SAVE CHANGES
        # ------------------------------------------

        connection.commit()

        print("\nDatabase migration completed successfully!")

    except Exception:

        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    migrate_database()