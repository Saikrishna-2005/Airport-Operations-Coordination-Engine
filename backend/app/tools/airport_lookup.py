import csv
from pathlib import Path
from functools import lru_cache


# --------------------------------------------------
# 1. GLOBAL AIRPORT DATASET PATH
# --------------------------------------------------

DATA_FILE = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "airports.csv"
)


# --------------------------------------------------
# 2. LOAD GLOBAL AIRPORT DATABASE
# --------------------------------------------------

@lru_cache(maxsize=1)
def load_airport_database() -> dict:
    """
    Load airport information from the OurAirports
    global airport dataset.

    Airports are indexed by their three-letter
    IATA codes.

    The dataset is loaded once per Python process.
    """

    airports = {}

    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Global airport dataset not found: {DATA_FILE}"
        )

    with DATA_FILE.open(
        mode="r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            code = (row.get("iata_code") or "").strip().upper()

            # Accept only valid three-letter IATA codes.
            if len(code) != 3 or not code.isalpha():
                continue

            # Exclude closed facilities.
            if row.get("type") == "closed":
                continue

            latitude = row.get("latitude_deg")
            longitude = row.get("longitude_deg")

            if not latitude or not longitude:
                continue

            try:
                latitude = float(latitude)
                longitude = float(longitude)
            except (ValueError, TypeError):
                continue

            if not (-90 <= latitude <= 90):
                continue

            if not (-180 <= longitude <= 180):
                continue

            airport = {
                "name": row.get("name") or "Unknown Airport",
                "city": row.get("municipality") or "Unknown",
                "country": row.get("iso_country") or "Unknown",
                "latitude": latitude,
                "longitude": longitude,
                "icao_code": row.get("icao_code") or "",
                "type": row.get("type") or "Unknown",
            }

            # Keep the first matching airport.
            # Duplicate IATA codes may require additional
            # disambiguation in a future version.
            if code not in airports:
                airports[code] = airport

    return airports


# --------------------------------------------------
# 3. LOOK UP AIRPORT USING IATA CODE
# --------------------------------------------------

def lookup_airport(airport_code: str) -> dict:
    """
    Find an airport using its three-letter IATA code.

    Returns airport details when found.
    Returns a descriptive error when not found.
    """

    if not isinstance(airport_code, str):
        return {
            "success": False,
            "reason": "Airport code must be a string.",
        }

    code = airport_code.strip().upper()

    if len(code) != 3 or not code.isalpha():
        return {
            "success": False,
            "reason": (
                "Airport code must contain exactly "
                "3 alphabetic characters."
            ),
        }

    airports = load_airport_database()

    airport = airports.get(code)

    if airport is None:
        return {
            "success": False,
            "reason": f"Airport code not found: {code}",
        }

    return {
        "success": True,
        "airport_code": code,
        **airport,
    }


# --------------------------------------------------
# 4. COUNT SUPPORTED AIRPORTS
# --------------------------------------------------

def get_supported_airport_count() -> int:
    """Return the number of indexed airport codes."""

    return len(load_airport_database())


# --------------------------------------------------
# 5. SEARCH GLOBAL AIRPORT DATABASE
# --------------------------------------------------

def search_airports(query: str, limit: int = 15) -> dict:
    """
    Search airports by:
    - IATA code
    - Airport name
    - City
    - Country code

    Returns up to 15 matching airports by default.
    """

    if not isinstance(query, str):
        return {
            "success": False,
            "reason": "Search query must be a string.",
        }

    search_text = query.strip().casefold()

    if len(search_text) < 2:
        return {
            "success": False,
            "reason": "Enter at least 2 characters to search.",
        }

    if not isinstance(limit, int) or not 1 <= limit <= 50:
        return {
            "success": False,
            "reason": "Search limit must be between 1 and 50.",
        }

    airports = load_airport_database()

    matches = []

    for code, airport in airports.items():

        name = airport["name"]
        city = airport["city"]
        country = airport["country"]

        searchable_fields = [
            code.casefold(),
            name.casefold(),
            city.casefold(),
            country.casefold(),
        ]

        if any(search_text in field for field in searchable_fields):

            # Prioritize exact IATA matches, then city/name matches.
            if code.casefold() == search_text:
                priority = 0
            elif city.casefold() == search_text:
                priority = 1
            elif name.casefold().startswith(search_text):
                priority = 2
            elif city.casefold().startswith(search_text):
                priority = 3
            else:
                priority = 4

            matches.append({
                "airport_code": code,
                "name": name,
                "city": city,
                "country": country,
                "latitude": airport["latitude"],
                "longitude": airport["longitude"],
                "priority": priority,
            })

    matches.sort(
        key=lambda airport: (
            airport["priority"],
            airport["name"].casefold(),
            airport["airport_code"],
        )
    )

    results = []

    for airport in matches[:limit]:
        results.append({
            key: value
            for key, value in airport.items()
            if key != "priority"
        })

    return {
        "success": True,
        "query": query.strip(),
        "count": len(results),
        "total_matches": len(matches),
        "airports": results,
    }