"""LangGraph state schema for the Weather Advisory Bot.

This defines the central state that flows through every node in the graph.
Each node reads from and writes to specific fields in this state.
"""

from typing import Annotated, Any

from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class LocationInfo(BaseModel):
    """Resolved location information."""

    name: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    country: str = ""
    admin1: str = ""  # State/region
    timezone: str = "auto"


class MatchedSOP(BaseModel):
    """An SOP that was matched against current conditions."""

    sop_id: str
    sop_name: str
    category: str
    severity: str  # "advisory", "moderate", "high", "critical"
    reason: str  # Why this SOP was triggered
    guidance: str  # The formatted guidance text


class AgentState(TypedDict):
    """The state that flows through the LangGraph agent.

    Each field is populated by a specific node in the graph:
    - messages: Accumulated chat history (append-only via add_messages)
    - user_query: The current user question (set by input)
    - location_name: Extracted location from the query (set by extract_intent)
    - activity: Extracted activity from the query (set by extract_intent)
    - location: Resolved geocoding result (set by fetch_weather node)
    - weather_data: Raw weather API response (set by fetch_weather node)
    - weather_summary: Formatted weather string for LLM (set by fetch_weather node)
    - matched_sops: List of SOPs that apply (set by match_sops node)
    - response: The final bot response (set by generate_response node)
    - error: Error description if something went wrong (set by any node)
    """

    # Chat history — uses LangGraph's add_messages reducer to append
    messages: Annotated[list, add_messages]

    # Input
    user_query: str

    # Extracted intent
    location_name: str
    activity: str

    # Location resolution
    location: dict[str, Any] | None

    # Weather data
    weather_data: dict[str, Any] | None
    weather_summary: str

    # SOP matching
    matched_sops: list[dict[str, Any]]

    # Output
    response: str

    # Error tracking
    error: str
