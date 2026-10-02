"""Geocoding utility to resolve city names to coordinates using Open-Meteo."""

import httpx
from app.config import settings


async def geocode_location(city_name: str) -> dict | None:
    """Resolve a city name to latitude/longitude using Open-Meteo Geocoding API.

    Args:
        city_name: Name of the city to geocode.

    Returns:
        Dict with 'name', 'latitude', 'longitude', 'country', 'admin1' (state/region)
        or None if the location could not be resolved.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                settings.GEOCODING_API_URL,
                params={"name": city_name, "count": 5, "language": "en", "format": "json"},
            )
            response.raise_for_status()
            data = response.json()

            if "results" not in data or len(data["results"]) == 0:
                return None

            # Take the first (most relevant) result
            result = data["results"][0]
            return {
                "name": result.get("name", city_name),
                "latitude": result["latitude"],
                "longitude": result["longitude"],
                "country": result.get("country", "Unknown"),
                "admin1": result.get("admin1", ""),  # State/region
                "timezone": result.get("timezone", "auto"),
            }

    except httpx.HTTPStatusError as e:
        print(f"Geocoding HTTP error for '{city_name}': {e.response.status_code}")
        return None
    except httpx.RequestError as e:
        print(f"Geocoding request error for '{city_name}': {e}")
        return None
    except (KeyError, IndexError) as e:
        print(f"Geocoding parse error for '{city_name}': {e}")
        return None
