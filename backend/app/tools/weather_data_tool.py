import httpx
import time

from datetime import datetime, timezone
from threading import Lock

from app.tools.airport_lookup import lookup_airport


# --------------------------------------------------
# 1. WEATHER CACHE CONFIGURATION
# --------------------------------------------------

# Cache duration: 5 minutes
CACHE_TTL_SECONDS = 300

# Store successful weather responses by airport code.
_weather_cache = {}

# Protect cache access and prevent duplicate requests.
_cache_lock = Lock()


# --------------------------------------------------
# 2. FETCH WEATHER FROM OPEN-METEO
# --------------------------------------------------

def _fetch_weather_from_provider(code: str, airport: dict) -> dict:
    """
    Fetch current weather from Open-Meteo using
    coordinates obtained from the global airport database.

    This function does not use the cache.
    """

    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": airport["latitude"],
        "longitude": airport["longitude"],
        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "precipitation,"
            "rain,"
            "weather_code,"
            "cloud_cover,"
            "wind_speed_10m,"
            "wind_gusts_10m,"
            "visibility"
        ),
        "timezone": "UTC",
        "forecast_days": 1,
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()

        current = payload.get("current")

        if not isinstance(current, dict):
            return {
                "success": False,
                "reason": (
                    "Weather provider returned "
                    "no current conditions."
                ),
            }

        return {
            "success": True,
            "airport_code": code,
            "airport_name": airport["name"],
            "latitude": airport["latitude"],
            "longitude": airport["longitude"],
            "observation_time": current.get("time"),
            "retrieved_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "temperature_c": current.get("temperature_2m"),
            "humidity_percent": current.get(
                "relative_humidity_2m"
            ),
            "precipitation_mm": current.get("precipitation"),
            "rain_mm": current.get("rain"),
            "weather_code": current.get("weather_code"),
            "cloud_cover_percent": current.get("cloud_cover"),
            "wind_speed_kmh": current.get("wind_speed_10m"),
            "wind_gusts_kmh": current.get("wind_gusts_10m"),
            "visibility_m": current.get("visibility"),
            "source": "Open-Meteo",
        }

    except httpx.HTTPError as exc:
        return {
            "success": False,
            "reason": f"Weather service request failed: {exc}",
        }

    except (ValueError, TypeError, KeyError) as exc:
        return {
            "success": False,
            "reason": f"Invalid weather service response: {exc}",
        }


# --------------------------------------------------
# 3. WEATHER DATA TOOL WITH GLOBAL AIRPORT LOOKUP
# --------------------------------------------------

def get_weather_data(airport_code: str) -> dict:
    """
    Retrieve weather for an airport using its IATA code.

    Airport coordinates come from the global
    OurAirports reference dataset.

    Successful weather responses are cached for
    five minutes.

    Source: Open-Meteo.

    This is general weather information,
    not aviation-certified METAR/TAF data.
    """

    # Validate and identify airport.
    airport = lookup_airport(airport_code)

    if not airport["success"]:
        return {
            "success": False,
            "reason": airport["reason"],
        }

    code = airport["airport_code"]

    # Prevent simultaneous requests from fetching
    # the same airport repeatedly.
    with _cache_lock:

        cached_entry = _weather_cache.get(code)

        if cached_entry is not None:
            age = time.monotonic() - cached_entry["cached_at"]

            if age < CACHE_TTL_SECONDS:
                return {
                    **cached_entry["data"],
                    "cached": True,
                }

        # Cache missing or expired.
        result = _fetch_weather_from_provider(code, airport)

        if result["success"]:
            _weather_cache[code] = {
                "data": result,
                "cached_at": time.monotonic(),
            }

            return {
                **result,
                "cached": False,
            }

        # Never fabricate weather data on provider failure.
        return result