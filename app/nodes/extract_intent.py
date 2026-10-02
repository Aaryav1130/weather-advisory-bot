"""Intent extraction node — parses the user's question to extract location and activity.

This node uses the LLM to understand what the user is asking about:
- WHERE they want to do the activity (location/city)
- WHAT activity they're asking about (cycling, picnic, etc.)

The LLM is used here because users phrase things in natural language:
"Can my kid play outside in Mumbai?" → location: Mumbai, activity: child outdoor play
"""

import json

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from app.config import settings
from app.models.state import AgentState


EXTRACTION_PROMPT = """You are a precise information extractor. Given a user's question about outdoor activity safety, extract:

1. **location**: The city or place name mentioned. If no specific location is mentioned, output "unknown".
2. **activity**: What outdoor activity they're asking about. Be specific (e.g., "cycling", "picnic", "dog walk", "hiking", "travel", "commute"). If unclear, output "general outdoor activity".

IMPORTANT RULES:
- If the user references a previous conversation (e.g., "what about evening?" or "same place"), use the context from previous messages to fill in missing information.
- Only extract information explicitly stated or clearly implied. Do NOT guess locations.
- Output ONLY valid JSON, no other text.

Output format:
{"location": "<city_name>", "activity": "<activity_type>"}

Examples:
- "Is it safe to bike in Bhopal today?" → {"location": "Bhopal", "activity": "cycling"}
- "Can I take my dog for a walk?" → {"location": "unknown", "activity": "dog walk"}
- "Should I plan a picnic in Delhi this afternoon?" → {"location": "Delhi", "activity": "picnic"}
- "Is it a good day for outdoor exercise?" → {"location": "unknown", "activity": "outdoor exercise"}
"""


async def extract_intent(state: AgentState) -> dict:
    """Extract location and activity intent from the user's query.

    Uses the LLM to parse natural language into structured location + activity.
    Falls back gracefully if extraction fails.
    """
    llm = ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model_name=settings.MODEL_NAME,
        temperature=0,  # Deterministic extraction
    )

    # Include recent message history for context (follow-up questions)
    messages = [SystemMessage(content=EXTRACTION_PROMPT)]

    # Add last few messages for context (session memory)
    history = state.get("messages", [])
    if history:
        # Include up to last 6 messages for context
        recent = history[-6:]
        for msg in recent:
            messages.append(msg)

    messages.append(
        HumanMessage(content=f"Extract location and activity from: \"{state['user_query']}\"")
    )

    try:
        response = await llm.ainvoke(messages)
        content = response.content.strip()

        # Parse JSON from response (handle markdown code blocks)
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        extracted = json.loads(content)
        location_name = extracted.get("location", "unknown")
        activity = extracted.get("activity", "general outdoor activity")

        return {
            "location_name": location_name,
            "activity": activity,
            "error": "",
        }

    except json.JSONDecodeError:
        # If LLM doesn't return valid JSON, try to extract manually
        return {
            "location_name": "unknown",
            "activity": "general outdoor activity",
            "error": "",
        }
    except Exception as e:
        return {
            "location_name": "unknown",
            "activity": "general outdoor activity",
            "error": f"Intent extraction failed: {str(e)}",
        }
