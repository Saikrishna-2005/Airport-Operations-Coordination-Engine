
"""Cross-provider aircraft identity resolution."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


# ============================================================
# IDENTITY STATUS
# ============================================================

class IdentityStatus(str, Enum):
    verified = "verified"
    unverified = "unverified"
    mismatch = "mismatch"
    ambiguous = "ambiguous"


@dataclass(frozen=True)
class AircraftIdentity:
    flight_number: str | None = None
    airline_iata: str | None = None
    airline_icao: str | None = None
    callsign: str | None = None
    registration: str | None = None
    icao24: str | None = None


@dataclass(frozen=True)
class IdentityResolution:
    status: IdentityStatus
    reason: str
    matched_fields: tuple[str, ...] = ()
    conflicting_fields: tuple[str, ...] = ()


# ============================================================
# IDENTIFIER NORMALIZATION
# ============================================================

def normalize_identifier(value: str | None) -> str | None:
    if not value:
        return None

    normalized = value.strip().upper()

    return normalized or None


def normalize_registration(
    value: str | None,
) -> str | None:

    normalized = normalize_identifier(value)

    if not normalized:
        return None

    normalized = re.sub(r"[\s-]+", "", normalized)

    if not re.fullmatch(r"[A-Z0-9]+", normalized):
        return None

    return normalized


def normalize_icao24(
    value: str | None,
) -> str | None:

    if not value:
        return None

    normalized = value.strip().lower()

    if not re.fullmatch(r"[0-9a-f]{6}", normalized):
        return None

    return normalized


# ============================================================
# CALLSIGN CANDIDATE GENERATION
# ============================================================

def generate_candidate_callsign(
    flight_number: str | None,
    airline_iata: str | None,
    airline_icao: str | None,
) -> str | None:
    """Generate a discovery candidate, not verified identity."""

    flight = normalize_identifier(flight_number)
    iata = normalize_identifier(airline_iata)
    icao = normalize_identifier(airline_icao)

    if not flight or not iata or not icao:
        return None

    if not re.fullmatch(r"[A-Z0-9]{2}", iata):
        return None

    if not re.fullmatch(r"[A-Z]{3}", icao):
        return None

    if not flight.startswith(iata):
        return None

    suffix = flight[len(iata):]

    if not re.fullmatch(r"[0-9]{1,4}[A-Z]?", suffix):
        return None

    return f"{icao}{suffix}"


# ============================================================
# CROSS-PROVIDER IDENTITY VERIFICATION
# ============================================================

def verify_aircraft_identity(
    primary: AircraftIdentity,
    secondary: AircraftIdentity,
) -> IdentityResolution:
    """Compare aircraft identities without guessing missing data."""

    matched = []
    conflicts = []

    primary_icao = normalize_icao24(primary.icao24)
    secondary_icao = normalize_icao24(secondary.icao24)

    primary_registration = normalize_registration(
        primary.registration
    )

    secondary_registration = normalize_registration(
        secondary.registration
    )

    primary_callsign = normalize_identifier(
        primary.callsign
    )

    secondary_callsign = normalize_identifier(
        secondary.callsign
    )

    # Compare ICAO24 addresses.
    if primary_icao and secondary_icao:
        if primary_icao == secondary_icao:
            matched.append("icao24")
        else:
            conflicts.append("icao24")

    # Compare aircraft registrations.
    if primary_registration and secondary_registration:
        if primary_registration == secondary_registration:
            matched.append("registration")
        else:
            conflicts.append("registration")

    # Callsign agreement is supporting evidence only.
    if primary_callsign and secondary_callsign:
        if primary_callsign == secondary_callsign:
            matched.append("callsign")

    # Contradictory aircraft identifiers prevent fusion.
    if conflicts:
        return IdentityResolution(
            status=IdentityStatus.mismatch,
            reason="Conflicting aircraft identifiers.",
            matched_fields=tuple(matched),
            conflicting_fields=tuple(conflicts),
        )

    # Matching ICAO24 addresses establish aircraft agreement,
    # but not necessarily the same flight instance.
    if "icao24" in matched:
        return IdentityResolution(
            status=IdentityStatus.verified,
            reason="Matching valid ICAO24 addresses.",
            matched_fields=tuple(matched),
        )

    return IdentityResolution(
        status=IdentityStatus.unverified,
        reason="Insufficient verified aircraft identifiers.",
        matched_fields=tuple(matched),
    )
