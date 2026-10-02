"""Fallback handler nodes — honest failure responses.

These nodes handle the various failure modes in the graph:
1. Location could not be resolved (geocoding failure)
2. Weather API is unreachable or returned an error
3. General errors

In all cases, the bot MUST fail honestly — never produce a plausible-sounding
guess or generic advice when it doesn't have the data to back it up.
"""

from langchain_core.messages import AIMessage, HumanMessage

from app.models.state import AgentState


async def handle_no_location(state: AgentState) -> dict:
    """Handle the case where no location was found in the user's query.

    The bot asks the user to specify a location rather than guessing.
    """
    user_query = state.get("user_query", "")
    response = (
        "I'd love to help with your outdoor activity question! However, I wasn't "
        "able to determine a specific location from your message. Could you please "
        "tell me which city or area you're asking about? For example: "
        "\"Is it safe to cycle in Mumbai today?\"\n\n"
        "I need a location to check the current weather conditions and give you "
        "accurate, policy-based advice."
    )

    return {
        "response": response,
        "messages": [
            HumanMessage(content=user_query),
            AIMessage(content=response),
        ],
    }


async def handle_geocoding_failure(state: AgentState) -> dict:
    """Handle the case where the location could not be geocoded.

    The bot honestly says it couldn't find the location rather than guessing.
    """
    location_name = state.get("location_name", "the location you mentioned")
    user_query = state.get("user_query", "")

    response = (
        f"I wasn't able to find weather data for \"{location_name}\" — I couldn't "
        f"resolve it to a specific location in our geocoding system. This could mean "
        f"the location name is misspelled, very specific (like a neighborhood), or "
        f"not in our database.\n\n"
        f"Could you try with a nearby city name instead? For example, instead of a "
        f"suburb name, try the main city."
    )

    return {
        "response": response,
        "messages": [
            HumanMessage(content=user_query),
            AIMessage(content=response),
        ],
    }


async def handle_weather_api_failure(state: AgentState) -> dict:
    """Handle the case where the weather API is unreachable.

    The bot MUST fail honestly — never produce a forecast it doesn't have.
    """
    location_name = state.get("location_name", "your location")
    user_query = state.get("user_query", "")

    response = (
        f"I'm sorry, I'm currently unable to fetch live weather data for "
        f"{location_name}. The weather service (Open-Meteo) appears to be "
        f"temporarily unavailable.\n\n"
        f"Without real-time weather data, I cannot provide accurate safety advice — "
        f"I won't guess or use outdated information. Please try again in a few "
        f"minutes, or check a local weather service like the IMD website "
        f"(mausam.imd.gov.in) for current conditions."
    )

    return {
        "response": response,
        "messages": [
            HumanMessage(content=user_query),
            AIMessage(content=response),
        ],
    }
