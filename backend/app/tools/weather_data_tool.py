import os
import time
import httpx

from datetime import datetime, timezone
from threading import Lock
from dotenv import load_dotenv

from app.tools.airport_lookup import lookup_airport


# --------------------------------------------------
# 1. CONFIGURATION
# --------------------------------------------------

load_dotenv()

WEATHERAPI_KEY = os.getenv("WEATHERAPI_KEY")

CACHE_TTL_SECONDS = 300
MAX_RETRIES = 3
REQUEST_TIMEOUT = 15.0

_weather_cache = {}
_cache_lock = Lock()


# --------------------------------------------------
# 2. COMMON WEATHER RESPONSE FORMAT
# --------------------------------------------------

def _build_weather_response(code, airport, current, source):

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
        "temperature_c": current.get("temperature_c"),
        "humidity_percent": current.get("humidity_percent"),
        "precipitation_mm": current.get("precipitation_mm"),
        "rain_mm": current.get("rain_mm"),
        "weather_code": current.get("weather_code"),
        "cloud_cover_percent": current.get("cloud_cover_percent"),
        "wind_speed_kmh": current.get("wind_speed_kmh"),
        "wind_gusts_kmh": current.get("wind_gusts_kmh"),
        "visibility_m": current.get("visibility_m"),
        "source": source,
    }


# --------------------------------------------------
# 3. PRIMARY PROVIDER - OPEN-METEO
# --------------------------------------------------

def _fetch_from_open_meteo(code, airport):

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

    retry_status_codes = {429, 500, 502, 503, 504}

    for attempt in range(MAX_RETRIES):

        try:
            with httpx.Client(timeout=REQUEST_TIMEOUT) as client:

                response = client.get(url, params=params)

                if response.status_code in retry_status_codes:

                    if attempt < MAX_RETRIES - 1:
                        time.sleep(2 ** attempt)
                        continue

                    return None

                response.raise_for_status()
                payload = response.json()

            current = payload.get("current")

            if not isinstance(current, dict):
                return None

            weather = {
                "time": current.get("time"),
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
            }

            return _build_weather_response(
                code, airport, weather, "Open-Meteo"
            )

        except (httpx.HTTPError, ValueError, TypeError, KeyError):

            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)

    return None


# --------------------------------------------------
# 4. BACKUP PROVIDER - WEATHERAPI
# --------------------------------------------------

def _fetch_from_weatherapi(code, airport):

    if not WEATHERAPI_KEY:
        return None

    url = "https://api.weatherapi.com/v1/current.json"

    params = {
        "key": WEATHERAPI_KEY,
        "q": (
            f"{airport['latitude']},"
            f"{airport['longitude']}"
        ),
    }

    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:

            response = client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()

        current = payload.get("current")

        if not isinstance(current, dict):
            return None

        weather = {
            "time": current.get("last_updated"),
            "temperature_c": current.get("temp_c"),
            "humidity_percent": current.get("humidity"),
            "precipitation_mm": current.get("precip_mm"),

            # WeatherAPI provides precipitation, not a
            # separate current rain measurement.
            "rain_mm": None,

            "weather_code": (
                current.get("condition", {}).get("code")
            ),
            "cloud_cover_percent": current.get("cloud"),
            "wind_speed_kmh": current.get("wind_kph"),
            "wind_gusts_kmh": current.get("gust_kph"),

            # WeatherAPI visibility is in kilometres.
            "visibility_m": (
                current.get("vis_km") * 1000
                if current.get("vis_km") is not None
                else None
            ),
        }

        return _build_weather_response(
            code, airport, weather, "WeatherAPI"
        )

    except (httpx.HTTPError, ValueError, TypeError, KeyError):

        return None


# --------------------------------------------------
# 5. MAIN WEATHER DATA TOOL
# --------------------------------------------------

def get_weather_data(airport_code: str) -> dict:

    airport = lookup_airport(airport_code)

    if not airport["success"]:
        return {
            "success": False,
            "reason": airport["reason"],
        }

    code = airport["airport_code"]

    # Check existing cache.
    with _cache_lock:
        cached_entry = _weather_cache.get(code)

    if cached_entry is not None:

        age = time.monotonic() - cached_entry["cached_at"]

        if age < CACHE_TTL_SECONDS:

            return {
                **cached_entry["data"],
                "cached": True,
                "stale": False,
            }

    # First try Open-Meteo.
    result = _fetch_from_open_meteo(code, airport)

    # If Open-Meteo fails, try WeatherAPI.
    if result is None:

        result = _fetch_from_weatherapi(code, airport)

    # Store successful response from either provider.
    if result is not None:

        with _cache_lock:
            _weather_cache[code] = {
                "data": result,
                "cached_at": time.monotonic(),
            }

        return {
            **result,
            "cached": False,
            "stale": False,
        }

    # If both providers fail, use old cached data.
    if cached_entry is not None:

        return {
            **cached_entry["data"],
            "success": True,
            "cached": True,
            "stale": True,
            "warning": (
                "Both weather providers are unavailable. "
                "Showing previously retrieved weather data. "
                "This information may be outdated."
            ),
        }

    # No provider or cached data is available.
    return {
        "success": False,
        "airport_code": code,
        "reason": (
            "Weather data is unavailable from both "
            "Open-Meteo and WeatherAPI."
        ),
        "cached": False,
        "stale": False,
    }