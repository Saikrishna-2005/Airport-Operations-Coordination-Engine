from app.database.flight_database import (
    initialize_flight_database
)

from app.database.connection import (
    get_db_connection
)


def test_flight_database():

    initialize_flight_database()

    connection = get_db_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name IN (
                  'flights',
                  'flight_risk_factors',
                  'flight_dependencies'
              )
            ORDER BY name
            """
        )

        tables = [
            row["name"]
            for row in cursor.fetchall()
        ]

        print("\nFlight Operations Database Tables:")

        for table in tables:
            print("✓", table)

        expected_tables = {
            "flights",
            "flight_risk_factors",
            "flight_dependencies",
        }

        assert set(tables) == expected_tables, (
            "Some Flight Operations tables are missing"
        )

        print(
            "\nFlight Operations database initialized successfully."
        )

    finally:

        connection.close()


if __name__ == "__main__":
    test_flight_database()