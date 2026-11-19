"""Cirium Sky API flight operational intelligence tool."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from uuid import uuid4

import httpx
import sqlite3
from email.utils import parsedate_to_datetime
import math
from app.research_agent.tools.api_quota import ApiQuota

from app.research_agent.config import settings
from app.research_agent.schemas import (
    DataMode, ErrorInfo, FlightLookupStatus, FlightResult,
    FlightOperationalData, FlightOperationalStatus, FlightFieldSource,
    SourceRecord,
)
from app.research_agent.tools.flight_tool import FlightToolOutput
from app.research_agent.tools.cirium_auth import (
    get_cirium_headers, is_cirium_configured,
)


from app.research_agent.tools.aircraft_identity import (
    generate_candidate_callsign, normalize_registration, normalize_identifier,
)


def _get_synthetic_database():
    """Generate simulated flight operational records."""
    now = datetime.now(timezone.utc)
    return {
        "AI101": FlightOperationalData(
            flight_number="AI101", callsign="AIC101", airline="Air India",
            icao24="8005b1", origin_airport="BOM", destination_airport="DEL",
            status=FlightOperationalStatus.delayed,
            scheduled_departure=now-timedelta(minutes=90),
            actual_departure=now-timedelta(minutes=60),
            scheduled_arrival=now+timedelta(minutes=30),
            estimated_arrival=now+timedelta(minutes=60),
            departure_delay_minutes=30, arrival_delay_minutes=30,
            departure_gate="G08", arrival_gate="G12",
            departure_terminal="2", arrival_terminal="3",
        ),
        "6E204": FlightOperationalData(
            flight_number="6E204", callsign="IGO204", airline="IndiGo",
            icao24="800a42", origin_airport="DEL", destination_airport="BLR",
            status=FlightOperationalStatus.scheduled,
            scheduled_departure=now+timedelta(minutes=45),
            estimated_departure=now+timedelta(minutes=45),
            scheduled_arrival=now+timedelta(minutes=165),
            estimated_arrival=now+timedelta(minutes=165),
            departure_delay_minutes=0, arrival_delay_minutes=0,
            departure_gate="G15", arrival_gate="G22",
            departure_terminal="1", arrival_terminal="1",
        ),
        "AI306": FlightOperationalData(
            flight_number="AI306", callsign="AIC306", airline="Air India",
            origin_airport="DEL", destination_airport="BOM",
            status=FlightOperationalStatus.cancelled,
            scheduled_departure=now+timedelta(minutes=90),
            scheduled_arrival=now+timedelta(minutes=210), departure_terminal="3",
        ),
        "6E512": FlightOperationalData(
            flight_number="6E512", callsign="IGO512", airline="IndiGo",
            origin_airport="HYD", destination_airport="VTZ",
            status=FlightOperationalStatus.delayed,
            scheduled_arrival=now+timedelta(minutes=20),
            estimated_arrival=now+timedelta(minutes=55),
            arrival_delay_minutes=35, arrival_gate="G04",
        ),
    }


def _field_sources(operational, source):
    return {
        f"operational_data.{name}": FlightFieldSource(
            provider=source.provider, source_id=source.source_id,
            data_timestamp=source.retrieved_at,
        )
        for name, value in operational.model_dump(exclude_none=True).items()
        if value != "unknown"
    }


def _get_synthetic_flights(airport_code, flight_identifiers):
    now = datetime.now(timezone.utc)
    airport = airport_code.strip().upper()
    source_id = f"flight-cirium-synthetic-{uuid4().hex}"
    database = _get_synthetic_database()
    source = SourceRecord(source_id=source_id, provider="cirium-synthetic",
                          data_type="synthetic", retrieved_at=now,
                          source_url="synthetic://flight/cirium")
    results = []
    for identifier in flight_identifiers:
        normalized = identifier.strip().upper()
        operational = next((f for f in database.values()
                            if normalized in {f.flight_number, f.callsign,
                                              (f.icao24 or "").upper()}
                            and airport in {f.origin_airport, f.destination_airport}), None)
        if operational is None:
            results.append(FlightResult(requested_identifier=identifier,
                status=FlightLookupStatus.not_found, provider=source.provider,
                data={"note": "No matching synthetic flight record."},
                source_id=source_id, source_ids=[source_id], providers=[source.provider]))
            continue
        results.append(FlightResult(requested_identifier=identifier,
            status=FlightLookupStatus.found, provider=source.provider,
            providers=[source.provider], data={"synthetic": True, "data_category": "operational"},
            operational_data=operational, source_id=source_id, source_ids=[source_id],
            field_sources=_field_sources(operational, source), data_timestamp=now))
    return FlightToolOutput(flights=results, sources=[source], errors=[])


def _error_response(flight_identifiers, code, message, retryable=False):
    return FlightToolOutput(flights=[FlightResult(requested_identifier=i,
        status=FlightLookupStatus.error, provider="cirium", data={"error": message, "code": code})
        for i in flight_identifiers], sources=[], errors=[ErrorInfo(tool="cirium_tool",
        code=code, message=message, retryable=retryable)])


# Live normalization: gate events are distinct from runway events.
CIRIUM_STATUS_MAP = {
    "A": FlightOperationalStatus.active,
    "C": FlightOperationalStatus.cancelled,
    "L": FlightOperationalStatus.landed,
    "S": FlightOperationalStatus.scheduled,
    "D": FlightOperationalStatus.diverted,
}


def _parse_cirium_datetime(value):
    if not isinstance(value, dict) or not isinstance(value.get("dateUtc"), str):
        return None
    try:
        parsed = datetime.fromisoformat(value["dateUtc"].replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo is not None else None
    except (ValueError, OverflowError):
        return None


def _normalize_cirium_flight(record, appendix):
    carrier = record.get("carrierFsCode")
    number = record.get("flightNumber")
    airline = next((a for a in appendix.get("airlines", [])
                    if a.get("fs") == carrier), {})
    times = record.get("operationalTimes") or {}
    delays = record.get("delays") or {}
    resources = record.get("airportResources") or {}
    code = airline.get("iata") or carrier
    return FlightOperationalData(
        flight_number=f"{code}{number}" if code and number else None,
        callsign=None, icao24=None, airline=airline.get("name"),
        origin_airport=record.get("departureAirportFsCode"),
        destination_airport=record.get("arrivalAirportFsCode"),
        status=CIRIUM_STATUS_MAP.get(record.get("status"), FlightOperationalStatus.unknown),
        scheduled_departure=_parse_cirium_datetime(times.get("scheduledGateDeparture")),
        scheduled_arrival=_parse_cirium_datetime(times.get("scheduledGateArrival")),
        estimated_departure=_parse_cirium_datetime(times.get("estimatedGateDeparture")),
        estimated_arrival=_parse_cirium_datetime(times.get("estimatedGateArrival")),
        actual_departure=_parse_cirium_datetime(times.get("actualGateDeparture")),
        actual_arrival=_parse_cirium_datetime(times.get("actualGateArrival")),
        departure_delay_minutes=delays.get("departureGateDelayMinutes"),
        arrival_delay_minutes=delays.get("arrivalGateDelayMinutes"),
        departure_gate=resources.get("departureGate"), arrival_gate=resources.get("arrivalGate"),
        departure_terminal=resources.get("departureTerminal"), arrival_terminal=resources.get("arrivalTerminal"),
    )


def _identity_metadata(record, appendix, operational):
    carrier = record.get("carrierFsCode")
    airline = next((a for a in appendix.get("airlines", [])
                    if a.get("fs") == carrier), {})
    equipment = record.get("flightEquipment") or {}
    return {
        "airline_iata": normalize_identifier(airline.get("iata")),
        "airline_icao": normalize_identifier(airline.get("icao")),
        "aircraft_registration": normalize_registration(equipment.get("tailNumber")),
        "candidate_callsign": generate_candidate_callsign(
            operational.flight_number, airline.get("iata"), airline.get("icao")),
    }


def _cooldown_seconds(response):
    minimum = settings.CIRIUM_COOLDOWN_SECONDS
    raw = response.headers.get("Retry-After", "")
    try:
        delay = float(raw)
    except ValueError:
        try:
            delay = (parsedate_to_datetime(raw) - datetime.now(timezone.utc)).total_seconds()
        except (ValueError, TypeError, OverflowError):
            delay = 0
    return max(minimum, delay) if math.isfinite(delay) else minimum


def _get_live_flights(airport_code, flight_identifiers, timeout_seconds, *, airport_board=False):
    if not is_cirium_configured():
        return _error_response(flight_identifiers, "CIRIUM_NOT_CONFIGURED", "Cirium credentials are not configured.")
    if airport_code.strip().upper() not in {"DEL", "VIDP"}:
        return _error_response(flight_identifiers, "AIRPORT_NOT_SUPPORTED", "Initial live Cirium lookup supports DEL only.")
    # DEL has a fixed UTC offset; no Windows timezone database dependency.
    now = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    start = (now - timedelta(hours=2)).replace(minute=0, second=0, microsecond=0)
    base_url = settings.CIRIUM_BASE_URL.rstrip("/")
    if base_url not in {"https://api.sky.cirium.com", "https://api.sky.cirium.com/v1"}:
        return _error_response(flight_identifiers, "INVALID_CIRIUM_BASE_URL", "Unexpected Cirium API base URL.")
    if not base_url.endswith("/v1"):
        base_url += "/v1"
    records, sources, errors = [], [], []
    try:
        headers = get_cirium_headers()
    except Exception:
        return _error_response(flight_identifiers, "CIRIUM_AUTH_ERROR", "Could not configure authentication.")
    if settings.CIRIUM_REQUEST_BUDGET == 0:
        return _error_response(flight_identifiers, "CIRIUM_BUDGET_EXHAUSTED", "Local Cirium request budget is zero.")
    try:
        quota = ApiQuota()
    except (sqlite3.Error, OSError, ValueError):
        return _error_response(flight_identifiers, "CIRIUM_QUOTA_UNAVAILABLE", "Local quota database unavailable; request blocked.")
    with httpx.Client(timeout=min(timeout_seconds, settings.CIRIUM_TIMEOUT_SECONDS), follow_redirects=False) as client:
        for direction in ("arrival", "departure"):
            url = (f"{base_url}/flights/status/{direction}-airport/DEL/"
                   f"{direction}-date/{start:%Y-%m-%d}/{direction}-hour/{start.hour}")
            try:
                decision = quota.reserve("cirium", "flight_status", f"{direction}_airport",
                    limit=settings.CIRIUM_REQUEST_BUDGET, mode="live",
                    initial_used=settings.CIRIUM_INITIAL_USED, protected=True)
            except (sqlite3.Error, OSError, ValueError):
                errors.append(ErrorInfo(tool="cirium_tool", code="CIRIUM_QUOTA_UNAVAILABLE",
                    message="Local quota reservation failed; request blocked.", retryable=False))
                break
            if not decision.allowed:
                errors.append(ErrorInfo(tool="cirium_tool",
                    code={"cooldown": "CIRIUM_COOLDOWN", "pending_request": "CIRIUM_PENDING_REQUEST"}.get(decision.reason, "CIRIUM_BUDGET_EXHAUSTED"),
                    message="Local Cirium quota policy blocked request.", retryable=decision.reason == "cooldown"))
                break
            try:
                response = client.get(url, headers=headers, params={"numHours": 6})
                try:
                    quota.finalize("cirium", "flight_status", decision.request_id,
                        cooldown_seconds=_cooldown_seconds(response) if response.status_code == 429 else None)
                except (sqlite3.Error, OSError, ValueError, OverflowError):
                    errors.append(ErrorInfo(tool="cirium_tool", code="CIRIUM_QUOTA_UNAVAILABLE",
                        message="Could not finalize request; unresolved marker blocks further live requests.", retryable=False))
                    break
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict) or not isinstance(payload.get("flightStatuses"), list):
                    raise ValueError("Invalid flight list")
                appendix = payload.get("appendix") or {}
                if not isinstance(appendix, dict):
                    raise ValueError("Invalid appendix")
                source = SourceRecord(source_id=f"flight-cirium-live-{uuid4().hex}",
                    provider="cirium", data_type="live", retrieved_at=datetime.now(timezone.utc),
                    source_url=url+"?numHours=6")
                sources.append(source)
                for record in payload["flightStatuses"]:
                    try:
                        operational = _normalize_cirium_flight(record, appendix)
                        if record.get("flightId") is None:
                            raise ValueError("Missing flight ID")
                        identity = _identity_metadata(record, appendix, operational)
                        records.append((record, operational, source, identity))
                    except (ValueError, TypeError, AttributeError):
                        errors.append(ErrorInfo(tool="cirium_tool", code="CIRIUM_NORMALIZATION_ERROR",
                            message="A Cirium record could not be normalized.", retryable=False))
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                errors.append(ErrorInfo(tool="cirium_tool", code=f"CIRIUM_HTTP_{status}",
                    message=f"Cirium {direction} lookup failed: HTTP {status}.", retryable=status == 429 or status >= 500))
                if status in {401, 403, 429}:
                    break
            except httpx.RequestError:
                errors.append(ErrorInfo(tool="cirium_tool", code="CIRIUM_NETWORK_ERROR",
                    message=f"Cirium {direction} network request failed; outcome unresolved.", retryable=False))
                break
            except (ValueError, TypeError):
                errors.append(ErrorInfo(tool="cirium_tool", code="CIRIUM_INVALID_RESPONSE",
                    message="Invalid Cirium API response.", retryable=False))
    if airport_board:
        # Keep distinct provider flight instances and direction-specific reports.
        rows = []
        for record, operational, source, identity in records:
            rows.append({"flight_id": str(record["flightId"]),
                         "operational_data": operational.model_dump(mode="json"),
                         "source_id": source.source_id,
                         "direction": "arrival" if "/arrival-airport/" in source.source_url else "departure"})
        return {"rows": rows, "sources": [x.model_dump(mode="json") for x in sources],
                "errors": [x.model_dump(mode="json") for x in errors]}
    results = []
    incomplete = bool(errors)
    for identifier in flight_identifiers:
        normalized = identifier.strip().upper()
        matches = {}
        for record, operational, source, identity in records:
            aliases = {(operational.flight_number or "").upper(),
                       f'{record.get("carrierFsCode") or ""}{record.get("flightNumber") or ""}'.upper()}
            if normalized in aliases:
                matches[record["flightId"]] = (operational, source, identity)
        if len(matches) != 1:
            ambiguous = len(matches) > 1
            results.append(FlightResult(requested_identifier=identifier, provider="cirium",
                status=FlightLookupStatus.error if ambiguous or incomplete else FlightLookupStatus.not_found,
                data={"note": "Multiple flight instances matched." if ambiguous else "No match confirmed in query window."},
                source_ids=[s.source_id for s in sources]))
            if ambiguous:
                errors.append(ErrorInfo(tool="cirium_tool", code="AMBIGUOUS_FLIGHT",
                    message=f"Multiple Cirium flight instances matched {identifier}.", retryable=False))
            continue
        flight_id, (operational, source, identity) = next(iter(matches.items()))
        results.append(FlightResult(requested_identifier=identifier, status=FlightLookupStatus.found,
            provider="cirium", providers=["cirium"], operational_data=operational,
            data={"synthetic": False, "data_category": "operational", "cirium_flight_id": flight_id, **{k: v for k, v in identity.items() if v is not None}},
            source_id=source.source_id, source_ids=[source.source_id],
            field_sources={**_field_sources(operational, source), **{
                f"data.{key}": FlightFieldSource(provider=source.provider,
                    source_id=source.source_id, data_timestamp=source.retrieved_at)
                for key, value in {"cirium_flight_id": flight_id, **identity}.items()
                if value is not None and key != "candidate_callsign"
            }}, data_timestamp=source.retrieved_at))
    return FlightToolOutput(flights=results, sources=sources, errors=errors)


def get_cirium_flights(airport_code: str, flight_identifiers: list[str],
                       research_requirements: list[str], *, mode: DataMode | str = DataMode.synthetic,
                       timeout_seconds: float = 30.0) -> FlightToolOutput:
    """Retrieve operational flight intelligence without persistent caching."""
    mode_str = mode.value if isinstance(mode, DataMode) else str(mode).lower()
    if mode_str not in {"live", "synthetic"}:
        return _error_response(flight_identifiers, "INVALID_DATA_MODE", "Data mode must be live or synthetic.")
    if not flight_identifiers:
        return FlightToolOutput(flights=[], sources=[], errors=[])
    if mode_str == "synthetic":
        return _get_synthetic_flights(airport_code, flight_identifiers)
    if not settings.CIRIUM_ENABLED:
        return _error_response(flight_identifiers, "CIRIUM_DISABLED", "Cirium live integration is currently disabled.")
    return _get_live_flights(airport_code, flight_identifiers, timeout_seconds)


def get_airport_board(airport_code):
    if airport_code not in {"DEL", "VIDP"}:
        raise ValueError("Only DEL is supported")
    mode = DataMode(settings.DATA_MODE)
    if mode == DataMode.synthetic:
        result = _get_synthetic_flights("DEL", list(_get_synthetic_database()))
        rows = []
        for item in result.flights:
            op = item.operational_data
            if op is None:
                continue
            for direction, airport in (("arrival", op.destination_airport), ("departure", op.origin_airport)):
                if airport == "DEL":
                    rows.append({"flight_id": item.requested_identifier, "direction": direction,
                                 "source_id": item.source_id, "operational_data": op.model_dump(mode="json")})
        return {"rows": rows, "sources": [x.model_dump(mode="json") for x in result.sources], "errors": [], "data_mode": "synthetic"}
    if not settings.CIRIUM_ENABLED:
        return {"rows": [], "sources": [], "errors": [{"code": "CIRIUM_DISABLED"}], "data_mode": "live"}
    result = _get_live_flights("DEL", [], settings.REQUEST_TIMEOUT_SECONDS, airport_board=True)
    if not isinstance(result, dict):
        result = {"rows": [], "sources": [], "errors": [x.model_dump(mode="json") for x in result.errors]}
    return {**result, "data_mode": "live"}
