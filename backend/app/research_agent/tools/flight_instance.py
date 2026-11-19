"""Conservative, offline verification of independently observed flight instances."""
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import re


class FlightInstanceStatus(str, Enum):
    verified = 'verified'
    unverified = 'unverified'
    mismatch = 'mismatch'
    stale = 'stale'


@dataclass(frozen=True)
class FlightInstanceEvidence:
    provider: str
    icao24: str | None = None
    callsign: str | None = None
    origin: str | None = None
    destination: str | None = None
    actual_runway_departure: datetime | None = None
    observed_at: datetime | None = None
    # True only for independently obtained, provider-observed evidence.
    independently_observed: bool = False


@dataclass(frozen=True)
class FlightInstanceResolution:
    status: FlightInstanceStatus
    reasons: tuple[str, ...]


def _identifier(value, pattern):
    value = (value or '').strip().upper()
    return value if re.fullmatch(pattern, value) else None


def _aware(value):
    return isinstance(value, datetime) and value.utcoffset() is not None


def verify_flight_instance(operational, tracking, *, now=None,
                           max_age_seconds=120, departure_tolerance_seconds=300):
    """Compare observed evidence only; never pass registry-derived identifiers.

    Airports must already be canonical ICAO airport codes. Departure times
    must refer to actual runway departure, not gate or scheduled times.
    Caller is responsible for validating source provenance and uniqueness.
    """
    now = datetime.now(timezone.utc) if now is None else now
    if not _aware(now) or not 0 < max_age_seconds <= 120 or not 0 <= departure_tolerance_seconds <= 300:
        raise ValueError('Invalid verification policy')
    if not _aware(tracking.observed_at):
        return FlightInstanceResolution(FlightInstanceStatus.unverified, ('missing_tracking_timestamp',))
    age = (now - tracking.observed_at).total_seconds()
    if not 0 <= age <= max_age_seconds:
        return FlightInstanceResolution(FlightInstanceStatus.stale, ('tracking_observation_outside_window',))
    missing, conflicts = [], []
    if (not operational.independently_observed or not tracking.independently_observed
            or not operational.provider.strip() or not tracking.provider.strip()
            or operational.provider.strip().lower() == tracking.provider.strip().lower()):
        missing.append('independent_provider_evidence')
    for field, pattern in [('icao24', r'[0-9A-F]{6}'), ('callsign', r'[A-Z0-9]{1,8}'),
                           ('origin', r'[A-Z]{4}'), ('destination', r'[A-Z]{4}')]:
        a = _identifier(getattr(operational, field), pattern)
        b = _identifier(getattr(tracking, field), pattern)
        if not a or not b:
            missing.append(field)
        elif a != b:
            conflicts.append(field)
    a, b = operational.actual_runway_departure, tracking.actual_runway_departure
    if not _aware(a) or not _aware(b):
        missing.append('actual_runway_departure')
    elif a > tracking.observed_at or b > tracking.observed_at:
        conflicts.append('departure_after_observation')
    elif abs((a-b).total_seconds()) > departure_tolerance_seconds:
        conflicts.append('actual_runway_departure')
    if conflicts:
        return FlightInstanceResolution(FlightInstanceStatus.mismatch, tuple(conflicts))
    if missing:
        return FlightInstanceResolution(FlightInstanceStatus.unverified, tuple(missing))
    # Matching evidence is still not proof of a unique flight instance.
    # Keep live fusion closed until a trusted instance linkage is available.
    return FlightInstanceResolution(FlightInstanceStatus.unverified, ('unique_flight_instance_linkage_required',))
