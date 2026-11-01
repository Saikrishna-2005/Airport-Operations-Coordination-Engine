import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

from app.database import staff_database
from app.tools.staff_availability_tool import check_staff_availability


def run_tests():
    with tempfile.TemporaryDirectory() as temporary_directory:

        database_path = (
            Path(temporary_directory) / "staff_availability_test.db"
        )

        def test_connection():
            connection = sqlite3.connect(database_path)
            connection.row_factory = sqlite3.Row
            return connection

        # Redirect only staff database operations to the test DB.
        with patch.object(
            staff_database,
            "get_db_connection",
            side_effect=test_connection,
        ):

            # ---------------------------------------
            # 1. Initialize test database
            # ---------------------------------------

            staff_database.initialize_staff_tables()

            connection = test_connection()

            try:
                # ---------------------------------------
                # 2. Create test staff
                # ---------------------------------------

                connection.executemany(
                    """
                    INSERT INTO staff_members (
                        staff_id,
                        full_name,
                        role,
                        employment_status
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    [
                        ("TEST001", "Test Staff One", "Ground Staff", "active"),
                        ("TEST002", "Test Staff Two", "Security", "inactive"),
                        ("TEST003", "Test Staff Three", "Ground Staff", "active"),
                    ],
                )

                # ---------------------------------------
                # 3. Create test shifts
                # ---------------------------------------

                connection.executemany(
                    """
                    INSERT INTO staff_shifts (
                        staff_id,
                        shift_date,
                        start_minute,
                        end_minute
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    [
                        # Normal shift: 09:00–17:00
                        ("TEST001", "2026-10-29", 540, 1020),

                        # Inactive staff shift
                        ("TEST002", "2026-10-29", 540, 1020),

                        # Overnight shift: 22:00–06:00
                        ("TEST003", "2026-10-29", 1320, 1800),
                    ],
                )

                # ---------------------------------------
                # 4. Create conflicting assignment
                # ---------------------------------------

                connection.execute(
                    """
                    INSERT INTO staff_assignments (
                        staff_id,
                        assignment_date,
                        gate_id,
                        task_name,
                        start_minute,
                        end_minute
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "TEST001",
                        "2026-10-29",
                        "TEST-GATE",
                        "Aircraft Boarding",
                        660,
                        720,
                    ),
                )

                connection.commit()

            finally:
                connection.close()

            # ---------------------------------------
            # 5. Execute availability tests
            # ---------------------------------------

            test_cases = [
                (
                    "Available during scheduled shift",
                    "TEST001",
                    "2026-10-29",
                    "09:00",
                    "10:00",
                    True,
                    "Staff member is available",
                ),
                (
                    "Outside scheduled shift",
                    "TEST001",
                    "2026-10-29",
                    "18:00",
                    "19:00",
                    False,
                    "No scheduled shift covers the requested time",
                ),
                (
                    "Inactive staff",
                    "TEST002",
                    "2026-10-29",
                    "09:00",
                    "10:00",
                    False,
                    "Staff member is inactive",
                ),
                (
                    "Conflicting assignment",
                    "TEST001",
                    "2026-10-29",
                    "11:30",
                    "12:30",
                    False,
                    "Staff member has a conflicting assignment",
                ),
                (
                    "Available before assignment",
                    "TEST001",
                    "2026-10-29",
                    "10:00",
                    "11:00",
                    True,
                    "Staff member is available",
                ),
                (
                    "Available after assignment",
                    "TEST001",
                    "2026-10-29",
                    "12:00",
                    "13:00",
                    True,
                    "Staff member is available",
                ),
                (
                    "Overnight shift availability",
                    "TEST003",
                    "2026-10-30",
                    "02:00",
                    "04:00",
                    True,
                    "Staff member is available",
                ),
                (
                    "Outside overnight shift",
                    "TEST003",
                    "2026-10-30",
                    "07:00",
                    "08:00",
                    False,
                    "No scheduled shift covers the requested time",
                ),
                (
                    "Nonexistent staff",
                    "UNKNOWN",
                    "2026-10-29",
                    "09:00",
                    "10:00",
                    False,
                    "Staff member not found",
                ),
            ]

            passed = 0

            for (
                name,
                staff_id,
                requested_date,
                start_time,
                end_time,
                expected_available,
                expected_reason,
            ) in test_cases:

                result = check_staff_availability(
                    staff_id=staff_id,
                    requested_date=requested_date,
                    start_time=start_time,
                    end_time=end_time,
                )

                assert result["available"] == expected_available, (
                    f"{name}: unexpected availability result: {result}"
                )

                assert result["reason"] == expected_reason, (
                    f"{name}: unexpected reason: {result}"
                )

                print(f"PASS: {name}")
                passed += 1

            print("\n" + "-" * 50)
            print(f"ALL {passed} STAFF AVAILABILITY TESTS PASSED")
            print("-" * 50)


if __name__ == "__main__":
    run_tests()