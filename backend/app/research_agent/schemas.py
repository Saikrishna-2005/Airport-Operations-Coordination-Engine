"""Data contracts and schemas for the Airport Operations Research Agent."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator

SCHEMA_VERSION: Literal["1.0"] = "1.0"


class DisruptionType(str, Enum):
    """Types of airport or flight disruptions."""

    weather = "weather"
    delay = "delay"
    runway = "runway"
    other = "other"


class DataMode(str, Enum):
    """Execution data mode."""

    live = "live"
    synthetic = "synthetic"


class ResultStatus(str, Enum):
    """Status of research execution.

    Callers should treat each status as:
    - success: All requested weather and flight research completed with complete evidence.
    - partial_success: Some evidence was obtained, but one or more queries failed or returned missing data.
    - no_data: Queries succeeded technically, but no matching observations or flights were found.
    - failed: Research could not be conducted due to complete service or tool failures.
    """

    success = "success"
    partial_success = "partial_success"
    no_data = "no_data"
    failed = "failed"


class WeatherStatus(str, Enum):
    """Status of weather data retrieval."""

    success = "success"
    unavailable = "unavailable"
    error = "error"


class WeatherDataType(str, Enum):
    """Weather data classification. Never call Open-Meteo METAR."""

    forecast = "forecast"
    current = "current"
    historical = "historical"
    synthetic = "synthetic"


class FlightLookupStatus(str, Enum):
    """Status of flight lookup."""

    found = "found"
    not_found = "not_found"
    unsupported = "unsupported"
    error = "error"


class FindingKind(str, Enum):
    """Classification of an analytical finding."""

    provider_fact = "provider_fact"
    inference = "inference"


def _ensure_timezone_aware(dt: datetime | None) -> datetime | None:
    if dt is not None and (dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None):
        raise ValueError("Datetime must be timezone-aware.")
    return dt


class ResearchRequest(BaseModel):
    """Inbound request contract for research agent."""

    request_id: str = Field(..., description="Unique ID for this research request.")
    workflow_id: str = Field(..., description="Correlating orchestration workflow ID.")
    airport_code: str = Field(
        ...,
        description="IATA (3-letter) or ICAO (4-letter) airport identifier.",
    )
    disruption_type: DisruptionType = Field(..., description="Category of disruption.")
    disruption_description: str = Field(
        ...,
        description="Text describing the operational disruption.",
    )
    affected_flights: list[str] = Field(
        default_factory=list,
        description="List of flight numbers or callsigns affected.",
    )
    research_requirements: list[str] = Field(
        ...,
        min_length=1,
        description="Specific research questions or topics to investigate.",
    )
    planning_objective: str | None = Field(
        default=None,
        description="High-level objective the research supports.",
    )
    as_of: datetime | None = Field(
        default=None,
        description="Timezone-aware effective time of inquiry.",
    )
    data_mode: DataMode = Field(
        default=DataMode.synthetic,
        description="Whether to use synthetic fixtures or live providers.",
    )

    @field_validator("request_id", "workflow_id", mode="before")
    @classmethod
    def reject_empty_ids(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_stripped = v.strip()
            if not v_stripped:
                raise ValueError("Identifier cannot be empty.")
            return v_stripped
        return v

    @field_validator("airport_code", mode="before")
    @classmethod
    def validate_and_normalize_airport_code(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise ValueError("airport_code must be a string.")
        code = v.strip().upper()
        if not (len(code) in (3, 4) and code.isalpha()):
            raise ValueError(
                "airport_code must be 3 or 4 alphabetic characters (IATA/ICAO code)."
            )
        return code

    @field_validator("as_of")
    @classmethod
    def validate_as_of_tz(cls, v: datetime | None) -> datetime | None:
        return _ensure_timezone_aware(v)


class SourceRecord(BaseModel):
    """Provenance record tracking an evidence source."""

    source_id: str = Field(..., description="Unique source identifier.")
    provider: str = Field(..., description="Provider name (e.g. open-meteo, opensky).")
    data_type: str = Field(
        ...,
        description="Nature of the data (forecast, current, synthetic, etc.).",
    )
    retrieved_at: datetime = Field(
        ...,
        description="UTC timezone-aware datetime when source was retrieved.",
    )
    source_url: str | None = Field(
        default=None,
        description="URL or endpoint from which data was retrieved.",
    )

    @field_validator("retrieved_at")
    @classmethod
    def validate_retrieved_at_tz(cls, v: datetime) -> datetime:
        res = _ensure_timezone_aware(v)
        assert res is not None
        return res


class WeatherResult(BaseModel):
    """Weather evidence payload."""

    status: WeatherStatus = Field(..., description="Status of weather retrieval.")
    provider: str = Field(..., description="Provider name.")
    data_type: WeatherDataType = Field(
        ...,
        description="forecast, current, historical, or synthetic. Never METAR.",
    )
    observations: dict[str, Any] = Field(
        default_factory=dict,
        description="Key-value observations or hourly values.",
    )
    units: dict[str, str] = Field(
        default_factory=dict,
        description="Units corresponding to observation keys.",
    )
    valid_time: datetime | None = Field(
        default=None,
        description="Validity timestamp of observation or forecast.",
    )
    source_id: str | None = Field(
        default=None,
        description="Source identifier matching sources list.",
    )

    @field_validator("valid_time")
    @classmethod
    def validate_valid_time_tz(cls, v: datetime | None) -> datetime | None:
        return _ensure_timezone_aware(v)


# ============================================================
# MULTI-PROVIDER FLIGHT INTELLIGENCE
# ============================================================

class FlightOperationalStatus(str, Enum):
    """Normalized operational flight status."""

    scheduled = "scheduled"
    active = "active"
    delayed = "delayed"
    landed = "landed"
    cancelled = "cancelled"
    diverted = "diverted"
    unknown = "unknown"


class FlightOperationalData(BaseModel):
    """Normalized operational flight information."""

    flight_number: str | None = None
    callsign: str | None = None
    airline: str | None = None
    icao24: str | None = None

    origin_airport: str | None = None
    destination_airport: str | None = None

    status: FlightOperationalStatus = FlightOperationalStatus.unknown

    scheduled_departure: datetime | None = None
    scheduled_arrival: datetime | None = None

    estimated_departure: datetime | None = None
    estimated_arrival: datetime | None = None

    actual_departure: datetime | None = None
    actual_arrival: datetime | None = None

    departure_delay_minutes: int | None = None
    arrival_delay_minutes: int | None = None

    departure_gate: str | None = None
    arrival_gate: str | None = None

    departure_terminal: str | None = None
    arrival_terminal: str | None = None

    @field_validator(
        "scheduled_departure",
        "scheduled_arrival",
        "estimated_departure",
        "estimated_arrival",
        "actual_departure",
        "actual_arrival",
    )
    @classmethod
    def validate_timestamps(cls, v):
        return _ensure_timezone_aware(v)


class FlightFieldSource(BaseModel):
    """Provenance of an individual flight information field."""

    provider: str
    source_id: str | None = None
    data_timestamp: datetime | None = None

    @field_validator("data_timestamp")
    @classmethod
    def validate_timestamp(cls, v):
        return _ensure_timezone_aware(v)


class FlightDataConflict(BaseModel):
    """Conflict detected between flight data providers."""

    field_name: str

    primary_provider: str
    secondary_provider: str

    primary_value: Any = None
    secondary_value: Any = None

    selected_provider: str | None = None
    selected_value: Any = None

    reason: str
    resolved: bool = False




class FlightResult(BaseModel):
    """Single or multi-provider flight evidence payload."""

    requested_identifier: str = Field(
        ...,
        description="Requested flight number or callsign.",
    )

    status: FlightLookupStatus = Field(
        ...,
        description="Flight lookup status.",
    )

    provider: str = Field(
        ...,
        description="Primary flight data provider.",
    )

    data: dict[str, Any] = Field(
        default_factory=dict,
        description="Aircraft tracking and flight evidence.",
    )

    data_timestamp: datetime | None = None

    source_id: str | None = None

    # Multi-provider extensions

    providers: list[str] = Field(default_factory=list)

    operational_data: FlightOperationalData | None = None

    source_ids: list[str] = Field(default_factory=list)

    field_sources: dict[str, FlightFieldSource] = Field(
        default_factory=dict,
    )

    conflicts: list[FlightDataConflict] = Field(
        default_factory=list,
    )

    missing_fields: list[str] = Field(
        default_factory=list,
    )

    @field_validator("data_timestamp")
    @classmethod
    def validate_data_timestamp_tz(
        cls, v: datetime | None
    ) -> datetime | None:
        return _ensure_timezone_aware(v)


class Finding(BaseModel):
    """Analytical finding with grounded citations and declared limitations."""

    finding: str = Field(..., description="Finding statement.")
    evidence_refs: list[str] = Field(
        default_factory=list,
        description="List of source_ids supporting this finding.",
    )
    kind: FindingKind = Field(
        ...,
        description="provider_fact if directly extracted, or inference.",
    )
    limitations: list[str] = Field(
        default_factory=list,
        description="Known uncertainties, caveats, or missing context.",
    )

    @model_validator(mode="after")
    def validate_provider_fact_has_evidence(self) -> Finding:
        if self.kind == FindingKind.provider_fact and not self.evidence_refs:
            raise ValueError(
                "Findings of kind 'provider_fact' must have at least one evidence_ref."
            )
        return self


class ErrorInfo(BaseModel):
    """Safe, secret-free error tracking."""

    tool: str = Field(..., description="Component or tool name reporting error.")
    code: str = Field(..., description="Standardized error code.")
    message: str = Field(
        ...,
        description="Sanitized error description with no secrets.",
    )
    retryable: bool = Field(
        ...,
        description="Whether this operation is potentially retryable.",
    )


class ResearchResult(BaseModel):
    """Public result schema for the Airport Operations Research Agent."""

    schema_version: Literal["1.0"] = Field(
        default=SCHEMA_VERSION,
        description="Schema contract version.",
    )
    request_id: str = Field(..., description="Original request ID.")
    workflow_id: str = Field(..., description="Correlating workflow ID.")
    agent: Literal["research_agent"] = Field(
        default="research_agent",
        description="Fixed agent identifier.",
    )
    status: ResultStatus = Field(
        ...,
        description="Execution status (success, partial_success, no_data, failed).",
    )
    airport_code: str = Field(..., description="Target airport code.")
    data_mode: DataMode = Field(..., description="live or synthetic mode.")
    summary: str = Field(
        ...,
        description="Grounded natural language advisory summary.",
    )
    weather: WeatherResult | None = Field(
        default=None,
        description="Weather observations and forecast.",
    )
    flights: list[FlightResult] = Field(
        default_factory=list,
        description="Flight state records.",
    )
    findings: list[Finding] = Field(
        default_factory=list,
        description="List of factual and inferential findings.",
    )
    sources: list[SourceRecord] = Field(
        default_factory=list,
        description="List of evidence provenance records.",
    )
    missing_information: list[str] = Field(
        default_factory=list,
        description="Identified data gaps or unavailable items.",
    )
    errors: list[ErrorInfo] = Field(
        default_factory=list,
        description="Errors encountered during execution.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when result was generated.",
    )

    @field_validator("created_at")
    @classmethod
    def validate_created_at_tz(cls, v: datetime) -> datetime:
        res = _ensure_timezone_aware(v)
        assert res is not None
        return res

    @model_validator(mode="after")
    def validate_evidence_refs_exist_in_sources(self) -> ResearchResult:
        known_sources = {s.source_id for s in self.sources}
        for idx, finding in enumerate(self.findings):
            for ref in finding.evidence_refs:
                if ref not in known_sources:
                    raise ValueError(
                        f"Finding at index {idx} references unknown source_id '{ref}'. "
                        f"All evidence_refs must exist in sources."
                    )
        return self
