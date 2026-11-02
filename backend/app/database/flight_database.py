from app.database.connection import get_db_connection
from app.logger import logger
from app.rule_engine.flight_risk import calculate_flight_risk

# ============================================================
# INITIALIZE FLIGHT OPERATIONS DATABASE
# ============================================================

def initialize_flight_database():

    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        # ====================================================
        # FLIGHTS TABLE
        # ====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS flights (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                flight_number TEXT NOT NULL,

                airline TEXT NOT NULL,

                origin_code TEXT NOT NULL,

                origin_name TEXT,

                destination_code TEXT NOT NULL,

                destination_name TEXT,

                aircraft_registration TEXT,

                aircraft_type TEXT,

                scheduled_departure TEXT NOT NULL,

                estimated_departure TEXT,

                actual_departure TEXT,

                scheduled_arrival TEXT NOT NULL,

                estimated_arrival TEXT,

                actual_arrival TEXT,

                status TEXT NOT NULL DEFAULT 'SCHEDULED',

                delay_minutes INTEGER NOT NULL DEFAULT 0
                    CHECK (delay_minutes >= 0),

                gate TEXT,

                terminal TEXT,

                risk_score INTEGER NOT NULL DEFAULT 0
                    CHECK (risk_score BETWEEN 0 AND 100),

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # ====================================================
        # FLIGHT RISK FACTORS TABLE
        # ====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS flight_risk_factors (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                flight_id INTEGER NOT NULL,

                factor_type TEXT NOT NULL,

                description TEXT,

                severity TEXT NOT NULL
                    CHECK (
                        severity IN (
                            'LOW',
                            'MEDIUM',
                            'HIGH',
                            'CRITICAL'
                        )
                    ),

                score INTEGER NOT NULL DEFAULT 0
                    CHECK (score BETWEEN 0 AND 100),

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (flight_id)
                    REFERENCES flights(id)
                    ON DELETE CASCADE
            )
            """
        )

        # ====================================================
        # FLIGHT DEPENDENCIES TABLE
        # ====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS flight_dependencies (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                flight_id INTEGER NOT NULL,

                dependent_flight_id INTEGER NOT NULL,

                dependency_type TEXT NOT NULL,

                minimum_turnaround_minutes INTEGER DEFAULT 0
                    CHECK (minimum_turnaround_minutes >= 0),

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (flight_id)
                    REFERENCES flights(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (dependent_flight_id)
                    REFERENCES flights(id)
                    ON DELETE CASCADE,

                CHECK (flight_id != dependent_flight_id)
            )
            """
        )

        # ====================================================
        # INDEXES
        # ====================================================

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_flights_number
            ON flights(flight_number)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_flights_status
            ON flights(status)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_flights_departure
            ON flights(scheduled_departure)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_flights_risk
            ON flights(risk_score)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_risk_factors_flight
            ON flight_risk_factors(flight_id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_dependencies_flight
            ON flight_dependencies(flight_id)
            """
        )

        connection.commit()

        logger.info(
            "Flight Operations database initialized successfully"
        )

    except Exception:

        connection.rollback()

        logger.exception(
            "Failed to initialize Flight Operations database"
        )

        raise

    finally:

        connection.close()

from datetime import datetime, timezone

from app.schemas.flight import FlightCreate, FlightUpdate


# ============================================================
# CREATE FLIGHT
# ============================================================

def create_flight(flight: FlightCreate) -> dict:
    connection = get_db_connection()

    try:
        data = flight.model_dump(mode="json")

        data["delay_minutes"] = calculate_flight_delay(
            scheduled_departure=data["scheduled_departure"],
            estimated_departure=data.get("estimated_departure"),
            actual_departure=data.get("actual_departure"),
        )

        # Only columns present in the flights table
        columns = [
            "flight_number",
            "airline",
            "origin_code",
            "origin_name",
            "destination_code",
            "destination_name",
            "aircraft_registration",
            "aircraft_type",
            "scheduled_departure",
            "estimated_departure",
            "actual_departure",
            "scheduled_arrival",
            "estimated_arrival",
            "actual_arrival",
            "status",
            "gate",
            "terminal",
            "delay_minutes",
        ]

        values = [data.get(column) for column in columns]

        placeholders = ", ".join(["?"] * len(columns))

        cursor = connection.execute(
            f"""
            INSERT INTO flights ({", ".join(columns)})
            VALUES ({placeholders})
            """,
            values,
        )

        flight_id = cursor.lastrowid

        # Calculate and save initial flight risk
        save_flight_risk(
            connection=connection,
            flight_id=flight_id,
        )

        connection.commit()

        logger.info("Flight created: %s", flight_id)

        return get_flight_by_id(flight_id)

    except Exception:
        connection.rollback()
        logger.exception("Failed to create flight")
        raise

    finally:
        connection.close()


# ============================================================
# GET ALL FLIGHTS
# ============================================================

def get_all_flights() -> list[dict]:
    connection = get_db_connection()

    try:
        rows = connection.execute(
            """
            SELECT *
            FROM flights
            ORDER BY scheduled_departure ASC, id ASC
            """
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()


# ============================================================
# GET FLIGHT BY ID
# ============================================================

def get_flight_by_id(flight_id: int) -> dict | None:
    connection = get_db_connection()

    try:
        row = connection.execute(
            """
            SELECT *
            FROM flights
            WHERE id = ?
            """,
            (flight_id,),
        ).fetchone()

        return dict(row) if row else None

    finally:
        connection.close()


# ============================================================
# UPDATE FLIGHT
# ============================================================

def update_flight(
    flight_id: int,
    flight: FlightUpdate,
) -> dict | None:

    connection = get_db_connection()

    try:
        existing = connection.execute(
            "SELECT * FROM flights WHERE id = ?",
            (flight_id,),
        ).fetchone()

        if existing is None:
            return None

        updates = flight.model_dump(
            exclude_unset=True,
            mode="json",
        )

        if not updates:
            return dict(existing)

        # Validate the resulting schedule, including partial updates.
        departure = updates.get(
            "scheduled_departure",
            existing["scheduled_departure"],
        )

        arrival = updates.get(
            "scheduled_arrival",
            existing["scheduled_arrival"],
        )

        if departure is None or arrival is None:
            raise ValueError(
                "Scheduled departure and arrival cannot be null"
            )

        if datetime.fromisoformat(arrival) <= datetime.fromisoformat(
            departure
        ):
            raise ValueError(
                "Scheduled arrival must be after scheduled departure"
            )

        # FlightUpdate only exposes approved flight columns.
        # Never interpolate arbitrary user-supplied column names.
        allowed_columns = {
            "airline",
            "origin_code",
            "origin_name",
            "destination_code",
            "destination_name",
            "aircraft_registration",
            "aircraft_type",
            "scheduled_departure",
            "scheduled_arrival",
            "estimated_departure",
            "estimated_arrival",
            "actual_departure",
            "actual_arrival",
            "status",
            "gate",
            "terminal",
        }

        if not set(updates).issubset(allowed_columns):
            raise ValueError("Unsupported flight update field")

        updates["updated_at"] = datetime.now(
            timezone.utc
        ).isoformat()

        # ====================================================
        # RECALCULATE DELAY WHEN DEPARTURE TIMES CHANGE
        # ====================================================

        delay_fields = {
            "scheduled_departure",
            "estimated_departure",
            "actual_departure",
        }

        if delay_fields.intersection(updates):

            scheduled_departure = updates.get(
                "scheduled_departure",
                existing["scheduled_departure"],
            )

            estimated_departure = updates.get(
                "estimated_departure",
                existing["estimated_departure"],
            )

            actual_departure = updates.get(
                "actual_departure",
                existing["actual_departure"],
            )

            updates["delay_minutes"] = calculate_flight_delay(
                scheduled_departure=scheduled_departure,
                estimated_departure=estimated_departure,
                actual_departure=actual_departure,
            )

        assignments = ", ".join(
            f"{column} = ?" for column in updates
        )

        values = list(updates.values()) + [flight_id]

        connection.execute(
            f"""
            UPDATE flights
            SET {assignments}
            WHERE id = ?
            """,
            values,
        )

        # Recalculate risk after flight updates
        if {"status", "delay_minutes"}.intersection(updates):

            save_flight_risk(
                connection=connection,
                flight_id=flight_id,
            )

        connection.commit()

        logger.info("Flight updated: %s", flight_id)

        return get_flight_by_id(flight_id)

    except Exception:
        connection.rollback()
        logger.exception("Failed to update flight")
        raise

    finally:
        connection.close()


# ============================================================
# DELETE FLIGHT
# ============================================================

def delete_flight(flight_id: int) -> bool:
    connection = get_db_connection()

    try:
        # Enable FK enforcement for this connection.
        connection.execute("PRAGMA foreign_keys = ON")

        cursor = connection.execute(
            """
            DELETE FROM flights
            WHERE id = ?
            """,
            (flight_id,),
        )

        connection.commit()

        deleted = cursor.rowcount > 0

        if deleted:
            logger.info("Flight deleted: %s", flight_id)

        return deleted

    except Exception:
        connection.rollback()
        logger.exception("Failed to delete flight")
        raise

    finally:
        connection.close()

# ============================================================
# AUTOMATIC FLIGHT DELAY CALCULATION
# ============================================================

def calculate_flight_delay(
    scheduled_departure: str,
    estimated_departure: str | None = None,
    actual_departure: str | None = None,
) -> int:

    scheduled = datetime.fromisoformat(
        scheduled_departure.replace("Z", "+00:00")
    )

    departure_time = (
        actual_departure
        if actual_departure is not None
        else estimated_departure
    )

    if departure_time is None:
        return 0

    departure = datetime.fromisoformat(
        departure_time.replace("Z", "+00:00")
    )

    delay = (
        departure - scheduled
    ).total_seconds() / 60

    return max(0, int(delay))

# ============================================================
# CALCULATE AND SAVE FLIGHT RISK
# ============================================================

def save_flight_risk(connection, flight_id: int) -> dict:

    flight = connection.execute(
        """
        SELECT id, delay_minutes, status
        FROM flights
        WHERE id = ?
        """,
        (flight_id,),
    ).fetchone()

    if flight is None:
        raise ValueError("Flight not found")

    # Calculate current operational risk
    result = calculate_flight_risk(
        delay_minutes=flight["delay_minutes"],
        status=flight["status"],
    )

    # Update flight risk score
    connection.execute(
        """
        UPDATE flights
        SET risk_score = ?
        WHERE id = ?
        """,
        (
            result["risk_score"],
            flight_id,
        ),
    )

    # Remove outdated calculated risk factors
    connection.execute(
        """
        DELETE FROM flight_risk_factors
        WHERE flight_id = ?
        AND factor_type IN (
            'DEPARTURE_DELAY',
            'FLIGHT_STATUS'
        )
        """,
        (flight_id,),
    )

    # Insert newly calculated risk factors
    for factor in result["risk_factors"]:

        connection.execute(
            """
            INSERT INTO flight_risk_factors (
                flight_id,
                factor_type,
                description,
                severity,
                score
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                flight_id,
                factor["factor_type"],
                factor["description"],
                factor["severity"],
                factor["score"],
            ),
        )

    return result

# ============================================================
# DYNAMIC FLIGHT OPERATIONAL PULSE
# ============================================================

def get_flight_operational_pulse() -> dict:

    connection = get_db_connection()

    try:
        row = connection.execute(
            """
            SELECT
                COUNT(*) AS total_flights,

                COALESCE(SUM(
                    CASE
                        WHEN status = 'SCHEDULED'
                        THEN 1 ELSE 0
                    END
                ), 0) AS scheduled_flights,

                COALESCE(SUM(
                    CASE
                        WHEN status = 'DELAYED'
                        THEN 1 ELSE 0
                    END
                ), 0) AS delayed_flights,

                COALESCE(SUM(
                    CASE
                        WHEN status IN ('DEPARTED', 'IN_AIR')
                        THEN 1 ELSE 0
                    END
                ), 0) AS departed_flights,

                COALESCE(SUM(
                    CASE
                        WHEN status IN ('ARRIVED', 'LANDED')
                        THEN 1 ELSE 0
                    END
                ), 0) AS arrived_flights,

                COALESCE(SUM(
                    CASE
                        WHEN status = 'CANCELLED'
                        THEN 1 ELSE 0
                    END
                ), 0) AS cancelled_flights,

                COALESCE(SUM(
                    CASE
                        WHEN risk_score >= 75
                        THEN 1 ELSE 0
                    END
                ), 0) AS critical_risk_flights,

                COALESCE(
                    ROUND(AVG(delay_minutes), 2),
                    0
                ) AS average_delay_minutes

            FROM flights
            """
        ).fetchone()

        return dict(row)

    finally:
        connection.close()

# ============================================================
# CREATE FLIGHT DEPENDENCY
# ============================================================

def create_flight_dependency(
    flight_id: int,
    dependent_flight_id: int,
    dependency_type: str,
    minimum_turnaround_minutes: int = 0,
) -> dict:

    if flight_id == dependent_flight_id:
        raise ValueError(
            "A flight cannot depend on itself"
        )

    if minimum_turnaround_minutes < 0:
        raise ValueError(
            "Minimum turnaround cannot be negative"
        )

    allowed_types = {
        "AIRCRAFT",
        "CREW",
        "PASSENGER_CONNECTION",
        "GATE",
    }

    dependency_type = dependency_type.upper()

    if dependency_type not in allowed_types:
        raise ValueError("Invalid dependency type")

    connection = get_db_connection()

    try:
        connection.execute("PRAGMA foreign_keys = ON")

        # Verify both flights exist
        rows = connection.execute(
            """
            SELECT id
            FROM flights
            WHERE id IN (?, ?)
            """,
            (flight_id, dependent_flight_id),
        ).fetchall()

        if len(rows) != 2:
            raise ValueError(
                "Both flights must exist"
            )

        # Prevent duplicate dependencies
        existing = connection.execute(
            """
            SELECT id
            FROM flight_dependencies
            WHERE flight_id = ?
              AND dependent_flight_id = ?
              AND dependency_type = ?
            """,
            (
                flight_id,
                dependent_flight_id,
                dependency_type,
            ),
        ).fetchone()

        if existing:
            raise ValueError(
                "Flight dependency already exists"
            )

        # Prevent dependency cycles
        # Example: A -> B -> C -> A
        cycle = connection.execute(
            """
            WITH RECURSIVE reachable(id) AS (
                SELECT dependent_flight_id
                FROM flight_dependencies
                WHERE flight_id = ?

                UNION

                SELECT fd.dependent_flight_id
                FROM flight_dependencies fd
                JOIN reachable r
                  ON fd.flight_id = r.id
            )
            SELECT 1
            FROM reachable
            WHERE id = ?
            LIMIT 1
            """,
            (dependent_flight_id, flight_id),
        ).fetchone()

        if cycle:
            raise ValueError(
                "Dependency would create a cycle"
            )

        cursor = connection.execute(
            """
            INSERT INTO flight_dependencies (
                flight_id,
                dependent_flight_id,
                dependency_type,
                minimum_turnaround_minutes
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                flight_id,
                dependent_flight_id,
                dependency_type,
                minimum_turnaround_minutes,
            ),
        )

        dependency_id = cursor.lastrowid

        connection.commit()

        return {
            "id": dependency_id,
            "flight_id": flight_id,
            "dependent_flight_id": dependent_flight_id,
            "dependency_type": dependency_type,
            "minimum_turnaround_minutes": (
                minimum_turnaround_minutes
            ),
        }

    except Exception:
        connection.rollback()
        logger.exception(
            "Failed to create flight dependency"
        )
        raise

    finally:
        connection.close()


# ============================================================
# GET FLIGHT DEPENDENCIES
# ============================================================

def get_flight_dependencies(
    flight_id: int,
) -> list[dict]:

    connection = get_db_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                fd.*,
                f.flight_number AS dependent_flight_number,
                f.status AS dependent_flight_status
            FROM flight_dependencies fd
            JOIN flights f
              ON f.id = fd.dependent_flight_id
            WHERE fd.flight_id = ?
            ORDER BY fd.id
            """,
            (flight_id,),
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()


# ============================================================
# DELETE FLIGHT DEPENDENCY
# ============================================================

def delete_flight_dependency(
    dependency_id: int,
) -> bool:

    connection = get_db_connection()

    try:
        cursor = connection.execute(
            """
            DELETE FROM flight_dependencies
            WHERE id = ?
            """,
            (dependency_id,),
        )

        connection.commit()

        return cursor.rowcount > 0

    except Exception:
        connection.rollback()
        logger.exception(
            "Failed to delete flight dependency"
        )
        raise

    finally:
        connection.close()

# ============================================================
# CALCULATE DIRECT FLIGHT DEPENDENCY IMPACTS
# ============================================================

def calculate_flight_dependency_impacts(
    flight_id: int,
    additional_delay_minutes: int = 0,
) -> list[dict]:

    from datetime import timedelta, timezone

    if additional_delay_minutes < 0:
        raise ValueError(
            "Additional delay cannot be negative"
        )

    connection = get_db_connection()

    try:
        # Retrieve the source flight
        source = connection.execute(
            """
            SELECT *
            FROM flights
            WHERE id = ?
            """,
            (flight_id,),
        ).fetchone()

        if source is None:
            raise ValueError("Source flight not found")

        # Retrieve directly dependent flights
        dependencies = connection.execute(
            """
            SELECT
                fd.id AS dependency_id,
                fd.dependency_type,
                fd.minimum_turnaround_minutes,

                f.id AS dependent_flight_id,
                f.flight_number AS dependent_flight_number,
                f.scheduled_departure,
                f.estimated_departure,
                f.actual_departure,
                f.status

            FROM flight_dependencies fd

            JOIN flights f
                ON f.id = fd.dependent_flight_id

            WHERE fd.flight_id = ?

            ORDER BY fd.id
            """,
            (flight_id,),
        ).fetchall()

        def parse_utc(value):
            if value is None:
                return None

            parsed = datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )

            if parsed.tzinfo is None:
                raise ValueError(
                    "Flight timestamps must include a timezone"
                )

            return parsed.astimezone(timezone.utc)

        source_arrival = (
            source["actual_arrival"]
            or source["estimated_arrival"]
            or source["scheduled_arrival"]
        )

        arrival_time = parse_utc(source_arrival)

        simulated_arrival = (
            arrival_time
            + timedelta(minutes=additional_delay_minutes)
        )

        impacts = []

        for dependency in dependencies:

            dependency_type = dependency["dependency_type"]

            # Aircraft turnaround is the first supported
            # quantitative dependency model.
            if dependency_type != "AIRCRAFT":
                impacts.append({
                    "dependency_id": dependency["dependency_id"],
                    "dependent_flight_id": (
                        dependency["dependent_flight_id"]
                    ),
                    "dependent_flight_number": (
                        dependency["dependent_flight_number"]
                    ),
                    "dependency_type": dependency_type,
                    "impact_minutes": None,
                    "impact_status": "NOT_MODELLED",
                    "reason": (
                        "Quantitative impact calculation is "
                        "not implemented for this dependency type"
                    ),
                })

                continue

            # Actual departures cannot be moved by a
            # planning simulation.
            if dependency["actual_departure"] is not None:
                impacts.append({
                    "dependency_id": dependency["dependency_id"],
                    "dependent_flight_id": (
                        dependency["dependent_flight_id"]
                    ),
                    "dependent_flight_number": (
                        dependency["dependent_flight_number"]
                    ),
                    "dependency_type": dependency_type,
                    "impact_minutes": 0,
                    "impact_status": "ALREADY_DEPARTED",
                    "reason": (
                        "Dependent flight has an actual "
                        "departure timestamp"
                    ),
                })

                continue

            scheduled_departure = parse_utc(
                dependency["scheduled_departure"]
            )

            estimated_departure = parse_utc(
                dependency["estimated_departure"]
            )

            # Existing planned departure is the baseline.
            baseline_departure = (
                estimated_departure
                or scheduled_departure
            )

            turnaround = timedelta(
                minutes=dependency[
                    "minimum_turnaround_minutes"
                ]
            )

            earliest_departure = (
                simulated_arrival + turnaround
            )

            additional_impact = max(
                0,
                int(
                    (
                        earliest_departure
                        - baseline_departure
                    ).total_seconds() // 60
                ),
            )

            impacts.append({
                "dependency_id": dependency["dependency_id"],
                "dependent_flight_id": (
                    dependency["dependent_flight_id"]
                ),
                "dependent_flight_number": (
                    dependency["dependent_flight_number"]
                ),
                "dependency_type": dependency_type,
                "impact_minutes": additional_impact,
                "impact_status": (
                    "AFFECTED"
                    if additional_impact > 0
                    else "UNAFFECTED"
                ),
                "baseline_departure": (
                    baseline_departure.isoformat()
                ),
                "earliest_departure": (
                    earliest_departure.isoformat()
                ),
                "projected_departure": (
                    max(
                        baseline_departure,
                        earliest_departure,
                    ).isoformat()
                ),
            })

        return impacts

    finally:
        connection.close()

# ============================================================
# GET FLIGHT RISK FACTORS
# ============================================================

def get_flight_risk_factors(flight_id: int) -> list[dict]:
    from app.database.connection import get_db_connection

    connection = get_db_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                id,
                flight_id,
                factor_type,
                description,
                severity,
                score,
                created_at
            FROM flight_risk_factors
            WHERE flight_id = ?
            ORDER BY score DESC, id ASC
            """,
            (flight_id,),
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()