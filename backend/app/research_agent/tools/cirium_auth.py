
"""
Cirium Sky API Static Token Authentication.

The API secret is sent directly in the Authorization header.
OAuth token exchange is not required.
"""

from __future__ import annotations

from app.research_agent.config import settings


class CiriumAuthenticationError(RuntimeError):
    """Raised when Cirium authentication is not configured."""


def get_cirium_headers() -> dict[str, str]:
    """Build authenticated headers for Cirium Sky API requests."""

    secret = settings.CIRIUM_CLIENT_SECRET.strip()

    if not secret:
        raise CiriumAuthenticationError(
            "CIRIUM_CLIENT_SECRET is not configured."
        )

    return {
        "Authorization": secret,
        "Accept": "application/json",
    }


def is_cirium_configured() -> bool:
    """Check whether the required Cirium credentials are configured."""

    return bool(
        settings.CIRIUM_CLIENT_SECRET.strip()
        and settings.CIRIUM_BASE_URL.strip()
    )
