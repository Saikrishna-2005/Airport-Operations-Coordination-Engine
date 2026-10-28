import sqlite3

from pydantic import BaseModel, Field, model_validator

from app.database.connection import get_db_connection
from app.rule_engine.gate_management import (
    GateAssignment,
    detect_gate_conflict,
)


class GateAvailabilityRequest(BaseModel):
    airport_code: str = Field(min_length=3, max_length=3)
    flight_number: str = Field(min_length=2)
    gate_id: str = Field(min_length=1)
    start_minute: int = Field(ge=0, le=1439)
    end_minute: int = Field(ge=1, le=1440)

    @model_validator(mode="after")
    def validate_time_interval(self):
        if self.end_minute <= self.start_minute:
            raise ValueError(
                "end_minute must be greater than start_minute"
            )
        return self


class GateAvailabilityResult(BaseModel):
    airport_code: str
    flight_number: str
    gate_id: str
    available: bool
    conflicting_flights: list[str] = Field(default_factory=list)
    alternative_gates: list[str] = Field(default_factory=list)

def check_gate_availability(
    request: GateAvailabilityRequest,
) -> GateAvailabilityResult:

    connection = get_db_connection()

    try:
        rows = connection.execute(
            """
            SELECT airport_code, flight_number, gate_id,
                   start_minute, end_minute
            FROM gate_assignments
            WHERE airport_code = ?
              AND gate_id = ?
              AND start_minute < ?
              AND end_minute > ?
            """,
            (
                request.airport_code,
                request.gate_id,
                request.end_minute,
                request.start_minute,
            ),
        ).fetchall()

    finally:
        connection.close()

    requested_assignment = GateAssignment(
        airport_code=request.airport_code,
        flight_number=request.flight_number,
        gate_id=request.gate_id,
        start_minute=request.start_minute,
        end_minute=request.end_minute,
    )

    conflicting_flights = []

    for row in rows:
        existing_assignment = GateAssignment(
            airport_code=row[0],
            flight_number=row[1],
            gate_id=row[2],
            start_minute=row[3],
            end_minute=row[4],
        )

        if detect_gate_conflict(
            requested_assignment,
            existing_assignment,
        ):
            conflicting_flights.append(
                existing_assignment.flight_number
            )

    return GateAvailabilityResult(
        airport_code=request.airport_code,
        flight_number=request.flight_number,
        gate_id=request.gate_id,
        available=len(conflicting_flights) == 0,
        conflicting_flights=conflicting_flights,
    )
    
def find_alternative_gates(
    request: GateAvailabilityRequest,
    candidate_gates: list[str],
) -> list[str]:

    available_gates = []

    for gate_id in candidate_gates:

        if gate_id == request.gate_id:
            continue

        alternative_request = request.model_copy(
            update={"gate_id": gate_id}
        )

        result = check_gate_availability(alternative_request)

        if result.available:
            available_gates.append(gate_id)

    return available_gates