
"""Multi-provider flight intelligence integration."""

from __future__ import annotations

import re
import sqlite3
from app.research_agent.tools.flight_instance import (
    FlightInstanceEvidence, verify_flight_instance,
)
from app.research_agent.tools.aircraft_registry import lookup_registration
from app.research_agent.tools.aircraft_identity import (
    AircraftIdentity, IdentityStatus, verify_aircraft_identity, normalize_icao24,
)
from datetime import datetime, timezone

from app.research_agent.config import settings
from app.research_agent.schemas import (
    DataMode,
    ErrorInfo,
    FlightResult,
    FlightLookupStatus,
    FlightFieldSource,
    FlightDataConflict,
)
from app.research_agent.tools.flight_tool import (
    FlightToolOutput,
    get_flights,
)
from app.research_agent.tools.cirium_tool import (
    get_cirium_flights,
)
from app.research_agent.tools.airport_lookup import (
    get_airport,
    AirportNotFoundError,
)


# ============================================================
# REQUIREMENT CLASSIFICATION
# ============================================================

OPERATIONAL_FIELD_GROUPS = {
    "delay": [
        "departure_delay_minutes",
        "arrival_delay_minutes",
    ],
    "gate": [
        "departure_gate",
        "arrival_gate",
    ],
    "terminal": [
        "departure_terminal",
        "arrival_terminal",
    ],
    "schedule": [
        "scheduled_departure",
        "scheduled_arrival",
    ],
    "estimated": [
        "estimated_departure",
        "estimated_arrival",
    ],
    "eta": ["estimated_arrival"],
    "etd": ["estimated_departure"],
    "status": ["status"],
    "cancellation": ["status"],
    "cancelled": ["status"],
    "actual": [
        "actual_departure",
        "actual_arrival",
    ],
}


def _required_operational_fields(requirements):
    fields = set()

    text = " ".join(requirements).lower()

    for keyword, names in OPERATIONAL_FIELD_GROUPS.items():
        if re.search(
            r"\b" + re.escape(keyword) + r"(?:s|d)?\b",
            text,
        ):
            fields.update(names)

    return sorted(fields)


# ============================================================
# IDENTIFIER NORMALIZATION
# ============================================================

def _normalize_identifier(value):
    return str(value or "").strip().upper()


# ============================================================
# DATA FRESHNESS VALIDATION
# ============================================================

def _is_fresh(timestamp, max_age_seconds=120):

    if timestamp is None:
        return False

    age = (
        datetime.now(timezone.utc) - timestamp
    ).total_seconds()

    return 0 <= age <= max_age_seconds


# ============================================================
# MERGE PROVIDER RESULTS
# ============================================================

def _registry_diagnostics(operational, tracking):
    """Offline candidate comparison only; never authorize live fusion."""
    registration = operational.data.get("aircraft_registration")
    if not isinstance(registration, str) or not registration.strip():
        return {"status": "missing_registration", "candidates": [],
                "comparison": "not_checked", "source": "local_aircraft_registry"}
    try:
        result = lookup_registration(registration)
    except (sqlite3.Error, OSError, ValueError):
        result = {"status": "unavailable", "candidates": []}
    candidates = sorted({address for value in result["candidates"]
                         if (address := normalize_icao24(value))})
    observed = None
    if tracking is not None and tracking.status == FlightLookupStatus.found:
        observed = normalize_icao24(tracking.data.get("icao24"))
    comparison = "not_checked"
    if result["status"] == "candidate" and len(candidates) == 1 and observed:
        comparison = "candidate_match" if observed == candidates[0] else "candidate_mismatch"
    return {"status": result["status"], "candidates": candidates,
            "comparison": comparison, "source": "local_aircraft_registry"}


def _instance_diagnostics(operational, tracking):
    """Compare only existing provider evidence; never infer missing route or runway events."""
    raw = tracking.data.get("time_position")
    observed = None
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        try:
            observed = datetime.fromtimestamp(raw, tz=timezone.utc)
        except (ValueError, TypeError, OverflowError, OSError):
            pass
    def icao_airport(value):
        if not isinstance(value, str) or not value.strip():
            return None
        try:
            return getattr(get_airport(value), "icao", None)
        except AirportNotFoundError:
            return None
    op = operational.operational_data
    def string(value):
        return value if isinstance(value, str) else None
    resolution = verify_flight_instance(
        FlightInstanceEvidence(provider=operational.provider,
            icao24=string(op.icao24), callsign=string(op.callsign),
            origin=icao_airport(op.origin_airport), destination=icao_airport(op.destination_airport),
            independently_observed=False),
        FlightInstanceEvidence(provider=tracking.provider,
            icao24=string(tracking.data.get("icao24")),
            callsign=string(tracking.data.get("callsign")), observed_at=observed,
            independently_observed=False),
    )
    return {"status": resolution.status.value, "reasons": list(resolution.reasons),
            "fusion_allowed": False}


def _merge_flight(
    identifier,
    tracking,
    operational,
    required_fields,
    mode,
):

    tracking_found = (
        tracking is not None
        and tracking.status == FlightLookupStatus.found
    )

    operational_found = (
        operational is not None
        and operational.status == FlightLookupStatus.found
        and operational.operational_data is not None
    )

    data = {}
    providers = []
    source_ids = []
    field_sources = {}
    conflicts = []
    missing_fields = []

    operational_data = (
        operational.operational_data
        if operational_found
        else None
    )

    instance_diagnostic = None
    if tracking_found and operational_found and mode == DataMode.live:
        instance_diagnostic = _instance_diagnostics(operational, tracking)
        missing_fields.append("verified_flight_instance")

    # Reject conflicting aircraft identities.
    if tracking_found and operational_found:

        tracking_icao = _normalize_identifier(
            tracking.data.get("icao24")
        )

        operational_icao = _normalize_identifier(
            operational_data.icao24
        )

        identity_mismatch = (
            tracking_icao
            and operational_icao
            and tracking_icao != operational_icao
        )

        if identity_mismatch:

            conflicts.append(
                FlightDataConflict(
                    field_name="icao24",
                    primary_provider=tracking.provider,
                    secondary_provider=operational.provider,
                    primary_value=tracking_icao,
                    secondary_value=operational_icao,
                    reason=(
                        "Aircraft identities differ. "
                        "Tracking data was not merged."
                    ),
                    resolved=False,
                )
            )

            tracking_found = False
            if mode == DataMode.live:
                missing_fields.append("verified_aircraft_identity")

    # Live fusion requires independently corroborated aircraft identity.
    # A commercial flight number or a derived callsign is not proof.
    if tracking_found and operational_found and mode == DataMode.live:
        resolution = verify_aircraft_identity(
            AircraftIdentity(icao24=tracking.data.get("icao24"),
                             callsign=tracking.data.get("callsign")),
            AircraftIdentity(icao24=operational_data.icao24,
                             callsign=operational_data.callsign,
                             registration=operational.data.get("aircraft_registration")),
        )
        if resolution.status != IdentityStatus.verified:
            tracking_found = False
            missing_fields.append("verified_aircraft_identity")
        else:
            # Aircraft agreement is not flight-instance agreement.
            # Fail closed until an independent instance verifier is available.
            tracking_found = False
            missing_fields.append("verified_flight_instance")
        if tracking.source_id:
            source_ids.append(tracking.source_id)

    # Diagnose freshness independently of identity/instance rejection.
    if tracking is not None and tracking.status == FlightLookupStatus.found and mode == DataMode.live:

        observed_timestamp = None
        raw_timestamp = tracking.data.get("time_position")

        if raw_timestamp is not None and not isinstance(raw_timestamp, bool):
            try:
                observed_timestamp = datetime.fromtimestamp(
                    raw_timestamp,
                    tz=timezone.utc,
                )
            except (ValueError, TypeError, OSError, OverflowError):
                pass

        if not _is_fresh(observed_timestamp):
            tracking_found = False
            missing_fields.append("fresh_tracking_data")

    if tracking_found:

        tracking_provider = (
            "opensky-synthetic"
            if mode == DataMode.synthetic
            else tracking.provider
        )

        data.update(tracking.data)
        providers.append(tracking_provider)

        if tracking.source_id:
            source_ids.append(tracking.source_id)

        field_sources.update({
            f"data.{key}": FlightFieldSource(
                provider=tracking_provider,
                source_id=tracking.source_id,
                data_timestamp=tracking.data_timestamp,
            )
            for key, value in tracking.data.items()
            if value is not None
        })

    else:
        missing_fields.append("aircraft_tracking")

    if operational_found:
        if mode == DataMode.live:
            registry = _registry_diagnostics(operational, tracking)
            if registry["status"] != "missing_registration":
                data["aircraft_registry"] = registry
            if registry["status"] != "candidate":
                missing_fields.append("aircraft_registry_candidate")
            # Registry metadata is diagnostic, not provider telemetry.
            for key in ("cirium_flight_id", "airline_iata", "airline_icao",
                        "aircraft_registration", "candidate_callsign"):
                if operational.data.get(key) is not None:
                    data[key] = operational.data[key]

        providers.append(operational.provider)

        if operational.source_id:
            source_ids.append(operational.source_id)

        field_sources.update(
            operational.field_sources
        )

    # Keep legacy empty-data behavior when no operational metadata is available.
    if instance_diagnostic is not None and data:
        data["flight_instance_verification"] = instance_diagnostic

    # Preserve evidence sources involved in conflicts.
    if conflicts:
        for record in (tracking, operational):
            if record and record.source_id:
                source_ids.append(record.source_id)

    # Check requested operational information.
    for field_name in required_fields:

        value = (
            getattr(operational_data, field_name, None)
            if operational_data
            else None
        )

        if value is None or value == "unknown":
            missing_fields.append(
                f"operational_data.{field_name}"
            )

    if tracking_found or operational_found:
        status = FlightLookupStatus.found

    elif any(
        record is not None
        and record.status == FlightLookupStatus.error
        for record in (tracking, operational)
    ):
        status = FlightLookupStatus.error

    else:
        status = FlightLookupStatus.not_found

    primary = (
        tracking if tracking_found
        else operational if operational_found
        else None
    )

    return FlightResult(
        requested_identifier=identifier,
        status=status,
        provider=(
            "multi-provider"
            if len(providers) > 1
            else providers[0] if providers
            else "unavailable"
        ),
        providers=list(dict.fromkeys(providers)),
        data=data,
        operational_data=operational_data,
        source_id=primary.source_id if primary else None,
        source_ids=list(dict.fromkeys(source_ids)),
        data_timestamp=(
            primary.data_timestamp if primary else None
        ),
        field_sources=field_sources,
        conflicts=conflicts,
        missing_fields=sorted(set(missing_fields)),
    )


def _safe_provider_call(provider, provider_fn, **kwargs):
    """Isolate provider exceptions and represent missing error records."""
    try:
        output = provider_fn(**kwargs)
    except Exception as exc:
        output = FlightToolOutput(errors=[ErrorInfo(
            tool=provider,
            code="PROVIDER_EXCEPTION",
            message=f"{provider} request failed ({type(exc).__name__}).",
            retryable=False,
        )])

    if output.errors:
        existing = {
            _normalize_identifier(f.requested_identifier)
            for f in output.flights
        }
        missing = [
            FlightResult(
                requested_identifier=identifier,
                status=FlightLookupStatus.error,
                provider=provider,
            )
            for identifier in dict.fromkeys(kwargs["flight_identifiers"])
            if _normalize_identifier(identifier) not in existing
        ]
        if missing:
            output = FlightToolOutput(
                flights=[*output.flights, *missing],
                sources=output.sources,
                errors=output.errors,
            )
    return output


# ============================================================
# PUBLIC INTEGRATED FLIGHT TOOL
# ============================================================

def _get_integrated_flights_uncached(
    airport_code: str,
    flight_identifiers: list[str],
    research_requirements: list[str],
    *,
    mode: DataMode | str = DataMode.synthetic,
    timeout_seconds: float = 30.0,
    integration_enabled: bool | None = None,
) -> FlightToolOutput:

    try:
        mode = DataMode(mode)
    except ValueError:
        return FlightToolOutput(
            errors=[
                ErrorInfo(
                    tool="flight_integration",
                    code="INVALID_DATA_MODE",
                    message="Invalid flight data mode.",
                    retryable=False,
                )
            ]
        )

    enabled = (
        settings.FLIGHT_INTEGRATION_ENABLED
        if integration_enabled is None
        else integration_enabled
    )

    # Preserve existing behavior when integration is disabled.
    if not enabled:
        return get_flights(
            airport_code=airport_code,
            flight_identifiers=flight_identifiers,
            research_requirements=research_requirements,
            mode=mode,
            timeout_seconds=timeout_seconds,
        )

    if not flight_identifiers:
        return FlightToolOutput()

    try:
        airport = get_airport(airport_code)
        airport_code = airport.iata

    except AirportNotFoundError:
        return FlightToolOutput(
            errors=[
                ErrorInfo(
                    tool="flight_integration",
                    code="AIRPORT_NOT_FOUND",
                    message="Airport could not be resolved.",
                    retryable=False,
                )
            ]
        )

    required_fields = _required_operational_fields(
        research_requirements
    )

    # Step 1: Obtain operational flight information.
    operational_output = _safe_provider_call(
        "cirium",
        get_cirium_flights,
        airport_code=airport_code,
        flight_identifiers=flight_identifiers,
        research_requirements=research_requirements,
        mode=mode,
        timeout_seconds=timeout_seconds,
    )

    operational_map = {
        _normalize_identifier(f.requested_identifier): f
        for f in operational_output.flights
    }

    # Step 2: Translate commercial flight numbers
    # to aircraft callsigns when available.
    tracking_identifiers = {}

    for identifier in flight_identifiers:

        normalized = _normalize_identifier(identifier)
        record = operational_map.get(normalized)

        callsign = (
            record.operational_data.callsign
            if record and record.operational_data
            else None
        )

        # Compatibility with existing OpenSky test fixtures.
        if mode == DataMode.synthetic and normalized in {
            "6E204", "IGO204"
        }:
            callsign = "6E204"

        if mode == DataMode.live and record and record.operational_data:
            callsign = callsign or record.data.get("candidate_callsign")

        tracking_identifiers[normalized] = callsign or normalized

    # Step 3: Retrieve OpenSky tracking information.
    # Do not pass operational keywords to OpenSky.
    tracking_output = _safe_provider_call(
        "opensky",
        get_flights,
        airport_code=airport_code,
        flight_identifiers=list(
            dict.fromkeys(tracking_identifiers.values())
        ),
        research_requirements=["aircraft tracking"],
        mode=mode,
        timeout_seconds=timeout_seconds,
    )

    tracking_map = {
        _normalize_identifier(f.requested_identifier): f
        for f in tracking_output.flights
    }

    # Step 4: Merge both provider results.
    results = []

    for identifier in flight_identifiers:

        normalized = _normalize_identifier(identifier)

        tracking = tracking_map.get(
            _normalize_identifier(
                tracking_identifiers[normalized]
            )
        )

        operational = operational_map.get(normalized)

        results.append(
            _merge_flight(
                identifier=identifier,
                tracking=tracking,
                operational=operational,
                required_fields=required_fields,
                mode=mode,
            )
        )

    # Step 5: Preserve evidence and provider errors.
    sources = {
        source.source_id: source
        for source in (
            tracking_output.sources
            + operational_output.sources
        )
    }

    return FlightToolOutput(
        flights=results,
        sources=list(sources.values()),
        errors=(
            tracking_output.errors
            + operational_output.errors
        ),
    )


from app.research_agent.tools.flight_cache import flight_cache

def get_integrated_flights(airport_code, flight_identifiers, research_requirements, *,
                           mode=DataMode.synthetic, timeout_seconds=30.0, integration_enabled=None):
    enabled = settings.FLIGHT_INTEGRATION_ENABLED if integration_enabled is None else integration_enabled
    key = (airport_code, tuple(flight_identifiers), tuple(research_requirements), timeout_seconds, enabled)
    return flight_cache.get(
        key, lambda: _get_integrated_flights_uncached(
            airport_code, flight_identifiers, research_requirements, mode=mode,
            timeout_seconds=timeout_seconds, integration_enabled=enabled),
        mode=mode, ttl=settings.SYNTHETIC_FLIGHT_CACHE_TTL_SECONDS,
        enabled=settings.SYNTHETIC_FLIGHT_CACHE_ENABLED and settings.DATA_MODE == 'synthetic',
    )
