"""Flight Tool integrating OpenSky Network live aircraft states and deterministic synthetic mode.

Documentation & Attribution Check:
----------------------------------
- Checked on: 2026-10-27
- Endpoint: https://opensky-network.org/api/states/all
- Bounding Box query parameters:
  - lamin: minimum latitude (decimal degrees)
  - lomin: minimum longitude (decimal degrees)
  - lamax: maximum latitude (decimal degrees)
  - lomax: maximum longitude (decimal degrees)
- State Vector fields (index mapping):
  0: icao24 (str)
  1: callsign (str, up to 8 chars)
  2: origin_country (str)
  3: time_position (int/null, unix ts)
  4: last_contact (int, unix ts)
  5: longitude (float/null)
  6: latitude (float/null)
  7: baro_altitude (float/null, meters)
  8: on_ground (bool)
  9: velocity (float/null, m/s)
  10: true_track (float/null, degrees)
  11: vertical_rate (float/null, m/s)
  12: sensors (list[int]/null)
  13: geo_altitude (float/null, meters)
  14: squawk (str/null)
  15: spi (bool)
  16: position_source (int)
  17: category (int, optional)
- Authentication & Rate Limits:
  - OpenSky migrated to OAuth2 client credentials flow (auth token endpoint:
    https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token).
  - Anonymous access is strictly rate-limited (~400 credits/day, min 10s between requests).
  - Authenticated accounts receive higher credit allowances.
- Important Scope Notice:
  - OpenSky provides ONLY live transponder state vectors.
  - It NEVER provides airline schedules, flight delays, passenger gates, cancellations, or estimated arrivals.
"""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any
import httpx
from pydantic import BaseModel, Field

from app.research_agent.schemas import (
    DataMode,
    ErrorInfo,
    FlightLookupStatus,
    FlightResult,
    SourceRecord,
)
from app.research_agent.tools.airport_lookup import AirportNotFoundError, get_airport

OPENSKY_STATES_URL = "https://opensky-network.org/api/states/all"
UNSUPPORTED_KEYWORDS = [
    "schedule",
    "scheduled",
    "delay",
    "delays",
    "delayed",
    "gate",
    "gates",
    "airline status",
    "cancellation",
    "cancelled",
    "estimated arrival",
    "eta",
    "etd",
]


class FlightToolOutput(BaseModel):
    """Internal envelope for Flight Tool outputs."""

    flights: list[FlightResult] = Field(default_factory=list)
    sources: list[SourceRecord] = Field(default_factory=list)
    errors: list[ErrorInfo] = Field(default_factory=list)


def _detect_unsupported_requirements(requirements: list[str]) -> list[str]:
    """Identify requirement terms that OpenSky live aircraft states cannot provide."""
    detected = set()
    for req in requirements:
        req_lower = req.lower()
        for kw in UNSUPPORTED_KEYWORDS:
            if re.search(r"\b" + re.escape(kw) + r"\b", req_lower):
                detected.add(kw)
    return sorted(list(detected))


def _clean_str(val: str | None) -> str:
    return val.strip() if val else ""


def _parse_unix_utc(ts: int | float | None) -> datetime | None:
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except Exception:
        return None


def _get_synthetic_flights(
    airport_code: str,
    flight_identifiers: list[str],
    unsupported_fields: list[str],
) -> FlightToolOutput:
    now_utc = datetime.now(timezone.utc)
    ts = int(now_utc.timestamp())
    source_id = f"flight-opensky-{airport_code}-{ts}"

    # Synthetic fixture data dictionary
    synth_db: dict[str, dict[str, Any]] = {
        "AIC101": {
            "icao24": "8005b1",
            "callsign": "AIC101",
            "origin_country": "India",
            "latitude": 28.60,
            "longitude": 77.15,
            "baro_altitude": 3200.0,
            "velocity": 140.0,
            "true_track": 110.0,
            "on_ground": False,
            "time_position": ts - 20,
        },
        "6E204": {
            "icao24": "800a42",
            "callsign": "6E204",
            "origin_country": "India",
            "latitude": 28.57,
            "longitude": 77.11,
            "baro_altitude": 220.0,
            "velocity": 0.0,
            "true_track": 280.0,
            "on_ground": True,
            "time_position": ts - 45,
        },
    }

    results: list[FlightResult] = []
    for identifier in flight_identifiers:
        ident_clean = _clean_str(identifier).upper()
        if unsupported_fields:
            results.append(
                FlightResult(
                    requested_identifier=identifier,
                    status=FlightLookupStatus.unsupported,
                    provider="synthetic",
                    data={
                        "unsupported_fields": unsupported_fields,
                        "reason": (
                            "Flight provider only provides live aircraft state vectors. "
                            f"Requested attributes {unsupported_fields} are unsupported."
                        ),
                    },
                    data_timestamp=now_utc,
                    source_id=source_id,
                )
            )
        elif ident_clean in synth_db:
            data = synth_db[ident_clean]
            data_ts = _parse_unix_utc(data.get("time_position")) or now_utc
            results.append(
                FlightResult(
                    requested_identifier=identifier,
                    status=FlightLookupStatus.found,
                    provider="synthetic",
                    data=data,
                    data_timestamp=data_ts,
                    source_id=source_id,
                )
            )
        else:
            results.append(
                FlightResult(
                    requested_identifier=identifier,
                    status=FlightLookupStatus.not_found,
                    provider="synthetic",
                    data={
                        "note": "Identifier not found in synthetic aircraft state database. Matching is by callsign only."
                    },
                    data_timestamp=None,
                    source_id=source_id,
                )
            )

    source = SourceRecord(
        source_id=source_id,
        provider="synthetic",
        data_type="synthetic",
        retrieved_at=now_utc,
        source_url="synthetic://flight/opensky",
    )

    return FlightToolOutput(flights=results, sources=[source], errors=[])


def get_flights(
    airport_code: str,
    flight_identifiers: list[str],
    research_requirements: list[str],
    *,
    mode: DataMode | str = DataMode.synthetic,
    timeout_seconds: float = 30.0,
    client: httpx.Client | None = None,
    bounding_box_radius_deg: float = 0.5,
) -> FlightToolOutput:
    """Retrieve aircraft states matching requested flight identifiers around an airport.

    Never raises exceptions to callers; errors are captured in FlightToolOutput.
    """
    mode_str = mode.value if isinstance(mode, DataMode) else str(mode)
    now_utc = datetime.now(timezone.utc)

    # 1. Unknown airport validation
    try:
        airport = get_airport(airport_code)
    except AirportNotFoundError:
        err = ErrorInfo(
            tool="flight_tool",
            code="AIRPORT_NOT_FOUND",
            message=f"Airport '{airport_code}' could not be resolved to geographic coordinates.",
            retryable=False,
        )
        flight_results = [
            FlightResult(
                requested_identifier=ident,
                status=FlightLookupStatus.error,
                provider="opensky" if mode_str == "live" else "synthetic",
                data={"error": "Airport not found."},
                data_timestamp=None,
                source_id=None,
            )
            for ident in flight_identifiers
        ]
        return FlightToolOutput(flights=flight_results, sources=[], errors=[err])

    # 2. Early return if no flight identifiers requested
    if not flight_identifiers:
        return FlightToolOutput(flights=[], sources=[], errors=[])

    # Check for unsupported requirements
    unsupported_fields = _detect_unsupported_requirements(research_requirements)

    # 3. Synthetic mode
    if mode_str == "synthetic":
        return _get_synthetic_flights(airport.iata, flight_identifiers, unsupported_fields)

    # 4. Live mode with OpenSky Network
    from app.research_agent.config import settings as app_settings
    from app.research_agent.tools.opensky_auth import global_auth_manager

    # Calculate bounding box coordinates
    lat = airport.latitude
    lon = airport.longitude
    params: dict[str, Any] = {
        "lamin": round(lat - bounding_box_radius_deg, 4),
        "lamax": round(lat + bounding_box_radius_deg, 4),
        "lomin": round(lon - bounding_box_radius_deg, 4),
        "lomax": round(lon + bounding_box_radius_deg, 4),
    }

    managed_client = False
    if client is None:
        client = httpx.Client(timeout=timeout_seconds)
        managed_client = True

    try:
        # Check OAuth2 credentials
        cid = (app_settings.FLIGHT_CLIENT_ID or "").strip()
        csec = (app_settings.FLIGHT_CLIENT_SECRET or "").strip()
        use_auth = bool(cid and csec)

        headers: dict[str, str] = {}
        token: str | None = None

        if use_auth:
            token, auth_err = global_auth_manager.get_token(cid, csec, client)
            if auth_err:
                # Token failure must produce error FlightResults for all identifiers and never silently fall back
                flight_results = [
                    FlightResult(
                        requested_identifier=ident,
                        status=FlightLookupStatus.error,
                        provider="opensky",
                        data={"error": auth_err.message, "code": auth_err.code},
                        data_timestamp=None,
                        source_id=None,
                    )
                    for ident in flight_identifiers
                ]
                return FlightToolOutput(flights=flight_results, sources=[], errors=[auth_err])
            headers["Authorization"] = f"Bearer {token}"

        response: httpx.Response | None = None
        last_error_code = ""
        last_error_message = ""
        retryable_error = False

        for attempt in range(2):
            try:
                response = client.get(OPENSKY_STATES_URL, params=params, headers=headers)
                if response.status_code == 200:
                    break
                elif response.status_code == 401 and use_auth:
                    # Token might have expired: invalidate cache and retry once with fresh token
                    global_auth_manager.clear()
                    token, auth_err = global_auth_manager.get_token(cid, csec, client, force_refresh=True)
                    if auth_err:
                        last_error_code = auth_err.code
                        last_error_message = auth_err.message
                        retryable_error = auth_err.retryable
                        break
                    headers["Authorization"] = f"Bearer {token}"
                    # Try states request once more
                    response = client.get(OPENSKY_STATES_URL, params=params, headers=headers)
                    if response.status_code == 200:
                        break
                    elif response.status_code in (401, 403):
                        last_error_code = "AUTH_FAILED"
                        last_error_message = f"OpenSky authentication failed (HTTP {response.status_code})."
                        retryable_error = False
                        break
                elif response.status_code == 429:
                    last_error_code = "RATE_LIMITED"
                    last_error_message = "OpenSky rate limit exceeded (HTTP 429)."
                    retryable_error = True
                    break  # no retry on 429
                elif response.status_code in (401, 403):
                    last_error_code = "AUTH_FAILED"
                    last_error_message = f"OpenSky authentication failed (HTTP {response.status_code})."
                    retryable_error = False
                    break  # no retry on auth failure
                elif 500 <= response.status_code < 600:
                    last_error_code = "PROVIDER_ERROR"
                    last_error_message = f"OpenSky upstream server error (HTTP {response.status_code})."
                    retryable_error = True
                    if attempt == 0:
                        continue  # retry once
                    break
                elif 400 <= response.status_code < 500:
                    last_error_code = "PROVIDER_REJECTED"
                    last_error_message = f"OpenSky rejected request (HTTP {response.status_code})."
                    retryable_error = False
                    break
                else:
                    last_error_code = "PROVIDER_ERROR"
                    last_error_message = f"Unexpected HTTP status {response.status_code}."
                    retryable_error = False
                    break
            except httpx.TimeoutException:
                last_error_code = "TIMEOUT"
                last_error_message = "OpenSky request timed out."
                retryable_error = True
                if attempt == 0:
                    continue  # retry once
                break
            except httpx.RequestError:
                last_error_code = "PROVIDER_ERROR"
                last_error_message = "Network error connecting to OpenSky."
                retryable_error = True
                if attempt == 0:
                    continue
                break

        # Handle non-200 outcome
        if response is None or response.status_code != 200:
            err = ErrorInfo(
                tool="flight_tool",
                code=last_error_code,
                message=last_error_message,
                retryable=retryable_error,
            )
            flight_results = [
                FlightResult(
                    requested_identifier=ident,
                    status=FlightLookupStatus.error,
                    provider="opensky",
                    data={"error": last_error_message, "code": last_error_code},
                    data_timestamp=None,
                    source_id=None,
                )
                for ident in flight_identifiers
            ]
            return FlightToolOutput(flights=flight_results, sources=[], errors=[err])

        # Parse JSON
        try:
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("Payload must be a JSON object.")
        except Exception:
            err = ErrorInfo(
                tool="flight_tool",
                code="INVALID_PAYLOAD",
                message="Malformed JSON returned by OpenSky.",
                retryable=False,
            )
            flight_results = [
                FlightResult(
                    requested_identifier=ident,
                    status=FlightLookupStatus.error,
                    provider="opensky",
                    data={"error": "Malformed JSON payload from provider."},
                    data_timestamp=None,
                    source_id=None,
                )
                for ident in flight_identifiers
            ]
            return FlightToolOutput(flights=flight_results, sources=[], errors=[err])

        ts = int(now_utc.timestamp())
        source_id = f"flight-opensky-{airport.iata}-{ts}"

        # Treat null 'states' as empty list (OpenSky returns null states when no aircraft are in the box)
        raw_states = payload.get("states")
        states_list: list[list[Any]] = raw_states if isinstance(raw_states, list) else []

        # Index states by trimmed, uppercase callsign
        callsign_to_states: dict[str, list[list[Any]]] = {}
        for state in states_list:
            if isinstance(state, list) and len(state) > 1 and state[1] is not None:
                cs = str(state[1]).strip().upper()
                if cs:
                    callsign_to_states.setdefault(cs, []).append(state)

        source_record = SourceRecord(
            source_id=source_id,
            provider="opensky",
            data_type="current",
            retrieved_at=now_utc,
            source_url="https://opensky-network.org/api/states/all",
        )

        flight_results = []
        errors: list[ErrorInfo] = []

        for ident in flight_identifiers:
            if unsupported_fields:
                flight_results.append(
                    FlightResult(
                        requested_identifier=ident,
                        status=FlightLookupStatus.unsupported,
                        provider="opensky",
                        data={
                            "unsupported_fields": unsupported_fields,
                            "reason": (
                                "OpenSky provides live aircraft state vectors only. "
                                f"Requested attributes {unsupported_fields} are unsupported."
                            ),
                        },
                        data_timestamp=now_utc,
                        source_id=source_id,
                    )
                )
                continue

            ident_clean = _clean_str(ident).upper()
            matching_states = callsign_to_states.get(ident_clean, [])

            if len(matching_states) == 1:
                st = matching_states[0]
                time_pos = st[3] if len(st) > 3 else None
                state_data = {
                    "icao24": st[0] if len(st) > 0 else None,
                    "callsign": str(st[1]).strip() if len(st) > 1 and st[1] else None,
                    "origin_country": st[2] if len(st) > 2 else None,
                    "time_position": time_pos,
                    "last_contact": st[4] if len(st) > 4 else None,
                    "longitude": st[5] if len(st) > 5 else None,
                    "latitude": st[6] if len(st) > 6 else None,
                    "baro_altitude": st[7] if len(st) > 7 else None,
                    "on_ground": st[8] if len(st) > 8 else None,
                    "velocity": st[9] if len(st) > 9 else None,
                    "true_track": st[10] if len(st) > 10 else None,
                    "vertical_rate": st[11] if len(st) > 11 else None,
                    "geo_altitude": st[13] if len(st) > 13 else None,
                    "squawk": st[14] if len(st) > 14 else None,
                }
                data_ts = _parse_unix_utc(time_pos) or now_utc
                flight_results.append(
                    FlightResult(
                        requested_identifier=ident,
                        status=FlightLookupStatus.found,
                        provider="opensky",
                        data=state_data,
                        data_timestamp=data_ts,
                        source_id=source_id,
                    )
                )
            elif len(matching_states) > 1:
                flight_results.append(
                    FlightResult(
                        requested_identifier=ident,
                        status=FlightLookupStatus.error,
                        provider="opensky",
                        data={
                            "error": f"Multiple aircraft ({len(matching_states)}) reported callsign '{ident_clean}'.",
                            "code": "AMBIGUOUS_MATCH",
                        },
                        data_timestamp=None,
                        source_id=source_id,
                    )
                )
                errors.append(
                    ErrorInfo(
                        tool="flight_tool",
                        code="AMBIGUOUS_MATCH",
                        message=f"Ambiguous match: {len(matching_states)} aircraft found for callsign '{ident_clean}'.",
                        retryable=False,
                    )
                )
            else:
                flight_results.append(
                    FlightResult(
                        requested_identifier=ident,
                        status=FlightLookupStatus.not_found,
                        provider="opensky",
                        data={
                            "note": (
                                f"Aircraft with callsign '{ident_clean}' not found within airport coverage area. "
                                "Matching is by exact callsign only (no commercial schedule translation)."
                            )
                        },
                        data_timestamp=None,
                        source_id=source_id,
                    )
                )

        return FlightToolOutput(flights=flight_results, sources=[source_record], errors=errors)

    finally:
        if managed_client:
            client.close()


# ============================================================
# AIRCRAFT IN AIRPORT COVERAGE AREA (LIVE MONITORING)
# ============================================================

def get_aircraft_in_area(
    airport_code: str,
    *,
    mode: DataMode | str = DataMode.synthetic,
    timeout_seconds: float = 30.0,
    client: httpx.Client | None = None,
    bounding_box_radius_deg: float = 0.5,
) -> dict[str, Any]:
    """Return every aircraft state vector currently reported in an airport bbox.

    This is intentionally separate from get_flights(), which performs exact
    callsign lookups. OpenSky state vectors do not establish airport arrivals
    or departures; the result is only aircraft detected in the coverage area.
    """
    mode_str = mode.value if isinstance(mode, DataMode) else str(mode).lower()
    now_utc = datetime.now(timezone.utc)

    try:
        airport = get_airport(airport_code)
    except AirportNotFoundError:
        return {
            "status": "error",
            "airport_code": airport_code.upper(),
            "provider": "opensky" if mode_str == "live" else "synthetic",
            "retrieved_at": now_utc.isoformat(),
            "aircraft_count": 0,
            "aircraft": [],
            "error": {
                "code": "AIRPORT_NOT_FOUND",
                "message": f"Airport '{airport_code}' could not be resolved.",
            },
        }

    if mode_str == "synthetic":
        ts = int(now_utc.timestamp())
        aircraft = [
            {
                "icao24": "8005b1", "callsign": "AIC101",
                "origin_country": "India", "time_position": ts - 20,
                "last_contact": ts - 10, "longitude": 28.6139,
                "latitude": 77.2090, "baro_altitude": 3200.0,
                "on_ground": False, "velocity": 140.0,
                "true_track": 110.0, "vertical_rate": 0.0,
                "geo_altitude": 3300.0, "squawk": "1234",
            },
            {
                "icao24": "800a42", "callsign": "6E204",
                "origin_country": "India", "time_position": ts - 45,
                "last_contact": ts - 20, "longitude": 28.5562,
                "latitude": 77.1000, "baro_altitude": 220.0,
                "on_ground": True, "velocity": 0.0,
                "true_track": 280.0, "vertical_rate": 0.0,
                "geo_altitude": 220.0, "squawk": "2345",
            },
        ]
        return {
            "status": "success",
            "airport_code": airport.iata,
            "airport_name": getattr(airport, "name", None),
            "provider": "synthetic",
            "retrieved_at": now_utc.isoformat(),
            "aircraft_count": len(aircraft),
            "aircraft": aircraft,
            "coverage": {
                "bounding_box_radius_degrees": bounding_box_radius_deg,
                "note": "Synthetic demonstration data; not live aircraft positions.",
            },
            "source": "synthetic://flight/aircraft-area",
            "errors": [],
        }

    if mode_str != "live":
        return {
            "status": "error",
            "airport_code": airport.iata,
            "provider": mode_str,
            "retrieved_at": now_utc.isoformat(),
            "aircraft_count": 0,
            "aircraft": [],
            "error": {"code": "INVALID_DATA_MODE", "message": "Mode must be 'live' or 'synthetic'."},
        }

    from app.research_agent.config import settings as app_settings
    from app.research_agent.tools.opensky_auth import global_auth_manager

    lat, lon = airport.latitude, airport.longitude
    params = {
        "lamin": round(lat - bounding_box_radius_deg, 4),
        "lamax": round(lat + bounding_box_radius_deg, 4),
        "lomin": round(lon - bounding_box_radius_deg, 4),
        "lomax": round(lon + bounding_box_radius_deg, 4),
    }

    managed_client = client is None
    if client is None:
        client = httpx.Client(timeout=timeout_seconds)

    try:
        cid = (app_settings.FLIGHT_CLIENT_ID or "").strip()
        csec = (app_settings.FLIGHT_CLIENT_SECRET or "").strip()
        headers: dict[str, str] = {}

        if cid and csec:
            token, auth_err = global_auth_manager.get_token(cid, csec, client)
            if auth_err:
                return {
                    "status": "error", "airport_code": airport.iata,
                    "provider": "opensky", "retrieved_at": now_utc.isoformat(),
                    "aircraft_count": 0, "aircraft": [],
                    "error": {"code": auth_err.code, "message": auth_err.message},
                }
            headers["Authorization"] = f"Bearer {token}"

        response = None
        last_error = None

        for attempt in range(2):
            try:
                response = client.get(OPENSKY_STATES_URL, params=params, headers=headers)
                if response.status_code == 200:
                    break
                if response.status_code == 401 and cid and csec:
                    global_auth_manager.clear()
                    token, auth_err = global_auth_manager.get_token(
                        cid, csec, client, force_refresh=True
                    )
                    if auth_err:
                        last_error = {"code": auth_err.code, "message": auth_err.message}
                        break
                    headers["Authorization"] = f"Bearer {token}"
                    response = client.get(OPENSKY_STATES_URL, params=params, headers=headers)
                    if response.status_code == 200:
                        break
                if response.status_code == 429:
                    last_error = {"code": "RATE_LIMITED", "message": "OpenSky rate limit exceeded."}
                    break
                if response.status_code in (401, 403):
                    last_error = {"code": "AUTH_FAILED", "message": f"OpenSky authentication failed (HTTP {response.status_code})."}
                    break
                if response.status_code >= 500 and attempt == 0:
                    continue
                last_error = {
                    "code": "PROVIDER_ERROR",
                    "message": f"OpenSky returned HTTP {response.status_code}.",
                }
                break
            except httpx.TimeoutException:
                last_error = {"code": "TIMEOUT", "message": "OpenSky request timed out."}
                if attempt == 0:
                    continue
                break
            except httpx.RequestError:
                last_error = {"code": "NETWORK_ERROR", "message": "Could not connect to OpenSky."}
                if attempt == 0:
                    continue
                break

        if response is None or response.status_code != 200:
            return {
                "status": "error", "airport_code": airport.iata,
                "provider": "opensky", "retrieved_at": now_utc.isoformat(),
                "aircraft_count": 0, "aircraft": [],
                "error": last_error or {"code": "PROVIDER_ERROR", "message": "OpenSky request failed."},
            }

        try:
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("Expected JSON object")
        except (ValueError, TypeError):
            return {
                "status": "error", "airport_code": airport.iata,
                "provider": "opensky", "retrieved_at": now_utc.isoformat(),
                "aircraft_count": 0, "aircraft": [],
                "error": {"code": "INVALID_PAYLOAD", "message": "OpenSky returned malformed JSON."},
            }

        raw_states = payload.get("states")
        aircraft = []
        for st in raw_states if isinstance(raw_states, list) else []:
            if not isinstance(st, list) or len(st) < 11:
                continue
            aircraft.append({
                "icao24": st[0],
                "callsign": str(st[1]).strip() if st[1] else None,
                "origin_country": st[2],
                "time_position": st[3] if len(st) > 3 else None,
                "last_contact": st[4] if len(st) > 4 else None,
                "longitude": st[5] if len(st) > 5 else None,
                "latitude": st[6] if len(st) > 6 else None,
                "baro_altitude": st[7] if len(st) > 7 else None,
                "on_ground": st[8] if len(st) > 8 else None,
                "velocity": st[9] if len(st) > 9 else None,
                "true_track": st[10] if len(st) > 10 else None,
                "vertical_rate": st[11] if len(st) > 11 else None,
                "geo_altitude": st[13] if len(st) > 13 else None,
                "squawk": st[14] if len(st) > 14 else None,
            })

        return {
            "status": "success",
            "airport_code": airport.iata,
            "airport_name": getattr(airport, "name", None),
            "provider": "opensky",
            "retrieved_at": now_utc.isoformat(),
            "aircraft_count": len(aircraft),
            "aircraft": aircraft,
            "coverage": {
                "lamin": params["lamin"], "lamax": params["lamax"],
                "lomin": params["lomin"], "lomax": params["lomax"],
                "bounding_box_radius_degrees": bounding_box_radius_deg,
                "note": "Aircraft detected in the geographic coverage area; not confirmed airport arrivals or departures.",
            },
            "source": OPENSKY_STATES_URL,
            "errors": [],
        }
    finally:
        if managed_client:
            client.close()


# ============================================================
# OPENSKY FLIGHT HISTORY, AIRPORT ARRIVALS/DEPARTURES & TRACKS
# ============================================================

OPENSKY_FLIGHTS_URL = "https://opensky-network.org/api/flights"
OPENSKY_TRACKS_URL = "https://opensky-network.org/api/tracks/all"


def _opensky_history_request(url: str, params: dict[str, Any], *, timeout_seconds: float = 30.0, client: httpx.Client | None = None) -> tuple[Any | None, dict[str, Any] | None]:
    """Authenticated OpenSky history request. Returns decoded JSON or a safe error."""
    from app.research_agent.config import settings as app_settings
    from app.research_agent.tools.opensky_auth import global_auth_manager
    managed_client = client is None
    if client is None:
        client = httpx.Client(timeout=timeout_seconds)
    try:
        cid = (app_settings.FLIGHT_CLIENT_ID or "").strip()
        csec = (app_settings.FLIGHT_CLIENT_SECRET or "").strip()
        headers: dict[str, str] = {}
        if cid and csec:
            token, auth_err = global_auth_manager.get_token(cid, csec, client)
            if auth_err:
                return None, {"code": auth_err.code, "message": auth_err.message}
            headers["Authorization"] = f"Bearer {token}"
        response = None
        for attempt in range(2):
            try:
                response = client.get(url, params=params, headers=headers)
                if response.status_code == 401 and cid and csec and attempt == 0:
                    global_auth_manager.clear()
                    token, auth_err = global_auth_manager.get_token(cid, csec, client, force_refresh=True)
                    if auth_err:
                        return None, {"code": auth_err.code, "message": auth_err.message}
                    headers["Authorization"] = f"Bearer {token}"
                    continue
                if response.status_code == 404:
                    return [], None
                if response.status_code == 429:
                    return None, {"code": "RATE_LIMITED", "message": "OpenSky rate limit exceeded; retry later."}
                if response.status_code in (401, 403):
                    return None, {"code": "AUTH_FAILED", "message": f"OpenSky authorization failed (HTTP {response.status_code})."}
                if response.status_code >= 500 and attempt == 0:
                    continue
                if response.status_code != 200:
                    return None, {"code": "PROVIDER_REJECTED", "message": f"OpenSky rejected the request (HTTP {response.status_code})."}
                try:
                    return response.json(), None
                except ValueError:
                    return None, {"code": "INVALID_PAYLOAD", "message": "OpenSky returned malformed JSON."}
            except httpx.TimeoutException:
                if attempt == 0: continue
                return None, {"code": "TIMEOUT", "message": "OpenSky request timed out."}
            except httpx.RequestError:
                if attempt == 0: continue
                return None, {"code": "NETWORK_ERROR", "message": "Could not connect to OpenSky."}
        return None, {"code": "PROVIDER_ERROR", "message": f"OpenSky request failed (HTTP {response.status_code})." if response is not None else "OpenSky request failed."}
    finally:
        if managed_client:
            client.close()


def _validate_opensky_interval(begin: int, end: int, *, max_seconds: int = 172800) -> None:
    if isinstance(begin, bool) or isinstance(end, bool) or begin <= 0 or end <= begin:
        raise ValueError("begin and end must be positive Unix timestamps, and end must be later than begin.")
    if end - begin > max_seconds:
        raise ValueError("This OpenSky endpoint supports a maximum interval of 2 days.")


def _normalize_flight_data(rows: Any) -> list[dict[str, Any]]:
    if rows is None: return []
    if not isinstance(rows, list): raise ValueError("OpenSky returned an unexpected flight-data format.")
    result=[]
    for row in rows:
        if not isinstance(row, dict): continue
        result.append({
            "icao24": row.get("icao24"), "callsign": (row.get("callsign") or "").strip() or None,
            "first_seen": row.get("firstSeen"), "estimated_departure_airport": row.get("estDepartureAirport"),
            "last_seen": row.get("lastSeen"), "estimated_arrival_airport": row.get("estArrivalAirport"),
            "departure_airport_horizontal_distance_m": row.get("estDepartureAirportHorizDistance"),
            "departure_airport_vertical_distance_m": row.get("estDepartureAirportVertDistance"),
            "arrival_airport_horizontal_distance_m": row.get("estArrivalAirportHorizDistance"),
            "arrival_airport_vertical_distance_m": row.get("estArrivalAirportVertDistance"),
            "departure_airport_candidates_count": row.get("departureAirportCandidatesCount"),
            "arrival_airport_candidates_count": row.get("arrivalAirportCandidatesCount"),
            "data_status": "historical_estimated",
        })
    return result


def get_arrivals_by_airport(airport_code: str, begin: int, end: int, *, timeout_seconds: float = 30.0, client: httpx.Client | None = None) -> dict[str, Any]:
    """Get historical estimated arrivals. Airport lookup must resolve to an ICAO code."""
    try:
        _validate_opensky_interval(begin, end); airport=get_airport(airport_code)
    except (ValueError, AirportNotFoundError) as exc:
        return {"status":"error","airport_code":airport_code.upper(),"flights":[],"error":{"code":"INVALID_AIRPORT_OR_INTERVAL","message":str(exc)}}
    icao=(getattr(airport,"icao",None) or "").strip().upper()
    if not icao:
        return {"status":"error","airport_code":airport.iata,"flights":[],"error":{"code":"AIRPORT_ICAO_REQUIRED","message":"Airport record has no ICAO code; OpenSky history requires ICAO."}}
    payload,error=_opensky_history_request(f"{OPENSKY_FLIGHTS_URL}/arrival",{"airport":icao,"begin":begin,"end":end},timeout_seconds=timeout_seconds,client=client)
    if error: return {"status":"error","airport_code":airport.iata,"airport_icao":icao,"flights":[],"error":error}
    try: flights=_normalize_flight_data(payload)
    except ValueError as exc: return {"status":"error","airport_code":airport.iata,"airport_icao":icao,"flights":[],"error":{"code":"INVALID_PAYLOAD","message":str(exc)}}
    return {"status":"success","airport_code":airport.iata,"airport_icao":icao,"provider":"opensky","data_status":"historical_estimated","begin":begin,"end":end,"count":len(flights),"flights":flights,"source":f"{OPENSKY_FLIGHTS_URL}/arrival"}


def get_departures_by_airport(airport_code: str, begin: int, end: int, *, timeout_seconds: float = 30.0, client: httpx.Client | None = None) -> dict[str, Any]:
    """Get historical estimated departures. Airport lookup must resolve to an ICAO code."""
    try:
        _validate_opensky_interval(begin, end); airport=get_airport(airport_code)
    except (ValueError, AirportNotFoundError) as exc:
        return {"status":"error","airport_code":airport_code.upper(),"flights":[],"error":{"code":"INVALID_AIRPORT_OR_INTERVAL","message":str(exc)}}
    icao=(getattr(airport,"icao",None) or "").strip().upper()
    if not icao:
        return {"status":"error","airport_code":airport.iata,"flights":[],"error":{"code":"AIRPORT_ICAO_REQUIRED","message":"Airport record has no ICAO code; OpenSky history requires ICAO."}}
    payload,error=_opensky_history_request(f"{OPENSKY_FLIGHTS_URL}/departure",{"airport":icao,"begin":begin,"end":end},timeout_seconds=timeout_seconds,client=client)
    if error: return {"status":"error","airport_code":airport.iata,"airport_icao":icao,"flights":[],"error":error}
    try: flights=_normalize_flight_data(payload)
    except ValueError as exc: return {"status":"error","airport_code":airport.iata,"airport_icao":icao,"flights":[],"error":{"code":"INVALID_PAYLOAD","message":str(exc)}}
    return {"status":"success","airport_code":airport.iata,"airport_icao":icao,"provider":"opensky","data_status":"historical_estimated","begin":begin,"end":end,"count":len(flights),"flights":flights,"source":f"{OPENSKY_FLIGHTS_URL}/departure"}


def get_flights_by_aircraft(icao24: str, begin: int, end: int, *, timeout_seconds: float = 30.0, client: httpx.Client | None = None) -> dict[str, Any]:
    address=(icao24 or "").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{6}",address): return {"status":"error","icao24":address,"flights":[],"error":{"code":"INVALID_ICAO24","message":"ICAO24 must be exactly 6 hexadecimal characters."}}
    try: _validate_opensky_interval(begin,end)
    except ValueError as exc: return {"status":"error","icao24":address,"flights":[],"error":{"code":"INVALID_INTERVAL","message":str(exc)}}
    payload,error=_opensky_history_request(f"{OPENSKY_FLIGHTS_URL}/aircraft",{"icao24":address,"begin":begin,"end":end},timeout_seconds=timeout_seconds,client=client)
    if error: return {"status":"error","icao24":address,"flights":[],"error":error}
    try: flights=_normalize_flight_data(payload)
    except ValueError as exc: return {"status":"error","icao24":address,"flights":[],"error":{"code":"INVALID_PAYLOAD","message":str(exc)}}
    return {"status":"success","icao24":address,"provider":"opensky","data_status":"historical_estimated","begin":begin,"end":end,"count":len(flights),"flights":flights,"source":f"{OPENSKY_FLIGHTS_URL}/aircraft"}


def get_flights_from_interval(begin: int, end: int, *, timeout_seconds: float = 30.0, client: httpx.Client | None = None) -> dict[str, Any]:
    """Get flights from a maximum two-hour UTC interval."""
    try: _validate_opensky_interval(begin,end,max_seconds=7200)
    except ValueError as exc: return {"status":"error","flights":[],"error":{"code":"INVALID_INTERVAL","message":str(exc)}}
    payload,error=_opensky_history_request(f"{OPENSKY_FLIGHTS_URL}/all",{"begin":begin,"end":end},timeout_seconds=timeout_seconds,client=client)
    if error: return {"status":"error","flights":[],"error":error}
    try: flights=_normalize_flight_data(payload)
    except ValueError as exc: return {"status":"error","flights":[],"error":{"code":"INVALID_PAYLOAD","message":str(exc)}}
    return {"status":"success","provider":"opensky","data_status":"historical_estimated","begin":begin,"end":end,"count":len(flights),"flights":flights,"source":f"{OPENSKY_FLIGHTS_URL}/all"}


def get_track_by_aircraft(icao24: str, timestamp: int = 0, *, timeout_seconds: float = 30.0, client: httpx.Client | None = None) -> dict[str, Any]:
    """Get an experimental trajectory. timestamp=0 requests a currently available live track."""
    address=(icao24 or "").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{6}",address): return {"status":"error","icao24":address,"path":[],"error":{"code":"INVALID_ICAO24","message":"ICAO24 must be exactly 6 hexadecimal characters."}}
    if isinstance(timestamp,bool) or timestamp<0: return {"status":"error","icao24":address,"path":[],"error":{"code":"INVALID_TIMESTAMP","message":"timestamp must be zero or a positive Unix timestamp."}}
    payload,error=_opensky_history_request(OPENSKY_TRACKS_URL,{"icao24":address,"time":timestamp},timeout_seconds=timeout_seconds,client=client)
    if error: return {"status":"error","icao24":address,"path":[],"error":error}
    if not isinstance(payload,dict): return {"status":"not_found","icao24":address,"path":[],"message":"No trajectory available for this aircraft and time."}
    path=[]
    for point in payload.get("path") or []:
        if isinstance(point,list): path.append({"time":point[0] if len(point)>0 else None,"latitude":point[1] if len(point)>1 else None,"longitude":point[2] if len(point)>2 else None,"baro_altitude":point[3] if len(point)>3 else None,"true_track":point[4] if len(point)>4 else None,"on_ground":point[5] if len(point)>5 else None})
    return {"status":"success","provider":"opensky","data_status":"experimental_trajectory" if timestamp==0 else "historical_trajectory","icao24":payload.get("icao24",address),"callsign":(payload.get("callSign") or payload.get("callsign") or "").strip() or None,"start_time":payload.get("startTime"),"end_time":payload.get("endTime"),"waypoint_count":len(path),"path":path,"source":OPENSKY_TRACKS_URL,"note":"OpenSky describes this tracks endpoint as experimental."}
