from app.database.connection import get_db_connection
from app.logger import logger


def initialize_gate_assignments_table():
    connection = get_db_connection()

    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS gate_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                airport_code TEXT NOT NULL,
                flight_number TEXT NOT NULL,
                gate_id TEXT NOT NULL,

                start_minute INTEGER NOT NULL
                    CHECK (start_minute BETWEEN 0 AND 1439),

                end_minute INTEGER NOT NULL
                    CHECK (end_minute BETWEEN 1 AND 1440),

                CHECK (end_minute > start_minute)
            )
            """
        )

        connection.commit()

        logger.info(
            "Gate assignments table initialized successfully"
        )

    except Exception:
        connection.rollback()
        logger.exception(
            "Failed to initialize gate assignments table"
        )
        raise

    finally:
        connection.close()