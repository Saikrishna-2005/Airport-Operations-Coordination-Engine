from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ============================================================
# FLIGHT STATUS
# ============================================================

FlightStatus = Literal[
    "SCHEDULED",
    "BOARDING",
    "DELAYED",
    "DEPARTED",
    "IN_AIR",
    "LANDED",
    "ARRIVED",
    "CANCELLED",
    "DIVERTED",
]


# ============================================================
# FLIGHT CREATE SCHEMA
# ============================================================

class FlightCreate(BaseModel):

    flight_number: str = Field(min_length=2, max_length=20)

    airline: str = Field(min_length=2, max_length=100)

    origin_code: str = Field(min_length=3, max_length=4)

    origin_name: str | None = None

    destination_code: str = Field(min_length=3, max_length=4)

    destination_name: str | None = None

    aircraft_registration: str | None = None

    aircraft_type: str | None = None

    scheduled_departure: datetime

    scheduled_arrival: datetime

    estimated_departure: datetime | None = None

    estimated_arrival: datetime | None = None

    actual_departure: datetime | None = None

    actual_arrival: datetime | None = None

    status: FlightStatus = "SCHEDULED"

    gate: str | None = None

    terminal: str | None = None

    @model_validator(mode="after")
    def validate_schedule(self):

        if self.scheduled_arrival <= self.scheduled_departure:
            raise ValueError(
                "Scheduled arrival must be after scheduled departure"
            )

        return self


# ============================================================
# FLIGHT UPDATE SCHEMA
# ============================================================

class FlightUpdate(BaseModel):

    airline: str | None = None

    origin_code: str | None = Field(
        default=None,
        min_length=3,
        max_length=4,
    )

    origin_name: str | None = None

    destination_code: str | None = Field(
        default=None,
        min_length=3,
        max_length=4,
    )

    destination_name: str | None = None

    aircraft_registration: str | None = None

    aircraft_type: str | None = None

    scheduled_departure: datetime | None = None

    scheduled_arrival: datetime | None = None

    estimated_departure: datetime | None = None

    estimated_arrival: datetime | None = None

    actual_departure: datetime | None = None

    actual_arrival: datetime | None = None

    status: FlightStatus | None = None

    gate: str | None = None

    terminal: str | None = None


# ============================================================
# AIRPORT INFORMATION
# ============================================================

class AirportInfo(BaseModel):

    code: str

    name: str | None = None


# ============================================================
# FLIGHT RESPONSE SCHEMA
# ============================================================

class FlightResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: int

    flight_number: str

    airline: str

    origin: AirportInfo

    destination: AirportInfo

    aircraft_registration: str | None = None

    aircraft_type: str | None = None

    scheduled_departure: datetime

    scheduled_arrival: datetime

    estimated_departure: datetime | None = None

    estimated_arrival: datetime | None = None

    actual_departure: datetime | None = None

    actual_arrival: datetime | None = None

    status: FlightStatus

    delay_minutes: int = Field(ge=0)

    gate: str | None = None

    terminal: str | None = None

    risk_score: int = Field(ge=0, le=100)


# ============================================================
# RISK FACTOR SCHEMA
# ============================================================

RiskSeverity = Literal[
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
]


class FlightRiskFactor(BaseModel):

    id: int

    flight_id: int

    factor_type: str

    description: str | None = None

    severity: RiskSeverity

    score: int = Field(ge=0, le=100)


# ============================================================
# FLIGHT DEPENDENCY SCHEMA
# ============================================================

class FlightDependency(BaseModel):

    id: int

    flight_id: int

    dependent_flight_id: int

    dependency_type: str

    minimum_turnaround_minutes: int = Field(ge=0)


# ============================================================
# OPERATIONAL PULSE SCHEMA
# ============================================================

class OperationalPulseResponse(BaseModel):

    total_flights: int = Field(ge=0)

    scheduled_flights: int = Field(ge=0)

    delayed_flights: int = Field(ge=0)

    departed_flights: int = Field(ge=0)

    arrived_flights: int = Field(ge=0)

    cancelled_flights: int = Field(ge=0)

    critical_risk_flights: int = Field(ge=0)

    average_delay_minutes: float = Field(ge=0)


# ============================================================
# FLIGHT DELAY SIMULATION
# ============================================================

class FlightSimulationRequest(BaseModel):

    flight_id: int = Field(gt=0)

    additional_delay_minutes: int = Field(
        ge=0,
        le=1440,
    )


class FlightSimulationResponse(BaseModel):

    flight_id: int

    original_delay_minutes: int = Field(ge=0)

    simulated_delay_minutes: int = Field(ge=0)

    affected_flights: list[int] = Field(
        default_factory=list
    )

    impact_description: str


# ============================================================
# API RESPONSE MESSAGE
# ============================================================

class FlightMessageResponse(BaseModel):

    message: str

    flight_id: int | None = None