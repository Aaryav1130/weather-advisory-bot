"""Weather data client using Open-Meteo API.

This module fetches REAL weather data from the API. The bot must never
report numbers that didn't come from this API — no model estimates or recalls.
"""

import httpx
from app.config import settings


async def fetch_weather(
    latitude: float,
    longitude: float,
    current_fields: list[str] | None = None,
    hourly_fields: list[str] | None = None,
) -> dict | None:
    """Fetch live weather data from Open-Meteo API.

    Args:
        latitude: Location latitude.
        longitude: Location longitude.
        current_fields: Fields for current weather (defaults to settings).
        hourly_fields: Fields for hourly forecast (defaults to settings).

    Returns:
        Dict containing weather data with 'current' and/or 'hourly' keys,
        or None if the API call failed.
    """
    if current_fields is None:
        current_fields = settings.CURRENT_WEATHER_FIELDS
    if hourly_fields is None:
        hourly_fields = settings.HOURLY_WEATHER_FIELDS

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": ",".join(current_fields),
        "hourly": ",".join(hourly_fields),
        "timezone": "auto",
        "forecast_days": 1,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(settings.WEATHER_API_URL, params=params)
            response.raise_for_status()
            data = response.json()

            # Validate that we got actual weather values, not just metadata
            if "current" not in data and "hourly" not in data:
                print("Weather API returned metadata only — no weather values.")
                return None

            return data

    except httpx.HTTPStatusError as e:
        print(f"Weather API HTTP error: {e.response.status_code}")
        return None
    except httpx.RequestError as e:
        print(f"Weather API request error: {e}")
        return None
    except Exception as e:
        print(f"Weather API unexpected error: {e}")
        return None


def format_weather_summary(weather_data: dict) -> str:
    """Format weather data into a human-readable summary for the LLM.

    This ensures the LLM has access to actual API numbers (not hallucinated ones)
    in a structured format it can reference in its response.
    """
    if not weather_data or "current" not in weather_data:
        return "Weather data unavailable."

    current = weather_data["current"]
    lines = ["=== CURRENT WEATHER DATA (from Open-Meteo API) ==="]

    field_labels = {
        "temperature_2m": ("Temperature", "°C"),
        "apparent_temperature": ("Feels Like", "°C"),
        "relative_humidity_2m": ("Humidity", "%"),
        "precipitation": ("Precipitation", "mm"),
        "rain": ("Rain", "mm"),
        "wind_speed_10m": ("Wind Speed", "km/h"),
        "wind_gusts_10m": ("Wind Gusts", "km/h"),
        "uv_index": ("UV Index", ""),
        "weather_code": ("Weather Code (WMO)", ""),
    }

    for field, (label, unit) in field_labels.items():
        if field in current:
            value = current[field]
            unit_str = f" {unit}" if unit else ""
            lines.append(f"  {label}: {value}{unit_str}")

    if "time" in current:
        lines.append(f"  Observation Time: {current['time']}")

    # Add hourly precipitation probability if available
    if "hourly" in weather_data:
        hourly = weather_data["hourly"]
        if "precipitation_probability" in hourly:
            probs = hourly["precipitation_probability"]
            # Get current and upcoming hours (next 6 hours)
            upcoming = probs[:6] if probs else []
            if upcoming:
                max_prob = max(upcoming)
                avg_prob = sum(upcoming) / len(upcoming)
                lines.append(f"  Precipitation Probability (next 6h max): {max_prob}%")
                lines.append(f"  Precipitation Probability (next 6h avg): {avg_prob:.0f}%")

    return "\n".join(lines)
