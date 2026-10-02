"""LangGraph agent definition — the core of the Weather Advisory Bot.

This module defines the computational graph that processes user queries:

    User Input → Extract Intent → Fetch Weather → Match SOPs → Generate Response
                                  ↓ (failure)      ↓ (no match)
                              Fallback Node     No-SOP Response

The graph has REAL branching at 3 decision points:
1. Can we resolve the location? (no location / geocoding failure path)
2. Did the weather API succeed? (API failure path)
3. Do any SOPs match? (no-policy path vs. grounded-response path)

This is a real LangGraph with conditional edges and dedicated failure nodes,
not a single function dressed up as a graph.
"""

from langgraph.graph import END, StateGraph

from app.models.state import AgentState
from app.nodes.extract_intent import extract_intent
from app.nodes.fallback import (
    handle_geocoding_failure,
    handle_no_location,
    handle_weather_api_failure,
)
from app.nodes.fetch_weather import fetch_weather_node
from app.nodes.generate_response import generate_response_node
from app.nodes.match_sops import match_sops_node


# =============================================================================
# Routing functions — these define the conditional branching in the graph
# =============================================================================


def route_after_weather_fetch(state: AgentState) -> str:
    """Route based on whether weather data was successfully fetched.

    Three possible outcomes:
    1. No location found → ask user to specify
    2. Geocoding or API failed → honest failure response
    3. Success → proceed to SOP matching
    """
    error = state.get("error", "")

    if error == "no_location":
        return "handle_no_location"
    elif error == "geocoding_failed":
        return "handle_geocoding_failure"
    elif error == "weather_api_failed":
        return "handle_weather_api_failure"
    elif state.get("weather_data") is None:
        return "handle_weather_api_failure"
    else:
        return "match_sops"


def route_after_sop_matching(state: AgentState) -> str:
    """Route based on whether any SOPs matched.

    The response generation node handles both cases (matched vs. no match)
    with different prompts, but both go to the same node. This is intentional —
    the generate_response node knows how to say "no SOP applies" honestly.
    """
    return "generate_response"


# =============================================================================
# Graph construction
# =============================================================================


def build_graph() -> StateGraph:
    """Build and compile the LangGraph agent.

    Returns a compiled graph that can process user queries through the
    full pipeline: intent → weather → SOP matching → response.
    """
    # Create the graph with our state schema
    graph = StateGraph(AgentState)

    # --- Add nodes ---
    graph.add_node("extract_intent", extract_intent)
    graph.add_node("fetch_weather", fetch_weather_node)
    graph.add_node("match_sops", match_sops_node)
    graph.add_node("generate_response", generate_response_node)

    # Fallback nodes for different failure modes
    graph.add_node("handle_no_location", handle_no_location)
    graph.add_node("handle_geocoding_failure", handle_geocoding_failure)
    graph.add_node("handle_weather_api_failure", handle_weather_api_failure)

    # --- Add edges ---

    # Start: always begin with intent extraction
    graph.set_entry_point("extract_intent")

    # After intent extraction, always try to fetch weather
    graph.add_edge("extract_intent", "fetch_weather")

    # BRANCHING POINT 1: After weather fetch, route based on success/failure
    graph.add_conditional_edges(
        "fetch_weather",
        route_after_weather_fetch,
        {
            "handle_no_location": "handle_no_location",
            "handle_geocoding_failure": "handle_geocoding_failure",
            "handle_weather_api_failure": "handle_weather_api_failure",
            "match_sops": "match_sops",
        },
    )

    # BRANCHING POINT 2: After SOP matching, proceed to response generation
    graph.add_conditional_edges(
        "match_sops",
        route_after_sop_matching,
        {
            "generate_response": "generate_response",
        },
    )

    # All terminal nodes lead to END
    graph.add_edge("generate_response", END)
    graph.add_edge("handle_no_location", END)
    graph.add_edge("handle_geocoding_failure", END)
    graph.add_edge("handle_weather_api_failure", END)

    return graph.compile()


# Singleton compiled graph instance
agent = build_graph()
