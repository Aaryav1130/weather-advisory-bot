"""Weather fetch node — resolves location and pulls live weather data.

This node is deterministic (no LLM involvement):
1. Geocodes the location name to lat/long
2. Calls Open-Meteo API for live weather data
3. Formats the data for the LLM to reference

All numbers in the bot's response will come from this node's API call,
ensuring the bot never hallucinates weather data.
"""

from app.models.state import AgentState
from app.utils.geocoding import geocode_location
from app.utils.weather_client import fetch_weather, format_weather_summary


async def fetch_weather_node(state: AgentState) -> dict:
    """Resolve location and fetch live weather data.

    This is a deterministic node — no LLM is used here.
    The weather numbers that flow into the response come exclusively from
    the Open-Meteo API via this node.
    """
    location_name = state.get("location_name", "unknown")

    # If no location was extracted, we can't fetch weather
    if not location_name or location_name.lower() == "unknown":
        return {
            "location": None,
            "weather_data": None,
            "weather_summary": "",
            "error": "no_location",
        }

    # Step 1: Geocode the location
    location = await geocode_location(location_name)

    if location is None:
        return {
            "location": None,
            "weather_data": None,
            "weather_summary": "",
            "error": "geocoding_failed",
        }

    # Step 2: Fetch weather data using resolved coordinates
    weather_data = await fetch_weather(
        latitude=location["latitude"],
        longitude=location["longitude"],
    )

    if weather_data is None:
        return {
            "location": location,
            "weather_data": None,
            "weather_summary": "",
            "error": "weather_api_failed",
        }

    # Step 3: Format weather data for the LLM
    weather_summary = format_weather_summary(weather_data)

    return {
        "location": location,
        "weather_data": weather_data,
        "weather_summary": weather_summary,
        "error": "",
    }
