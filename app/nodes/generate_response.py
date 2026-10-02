"""Response generation node — composes the final user-facing response.

This node uses the LLM to compose natural language, but it is CONSTRAINED:
- It can ONLY give advice that comes from matched SOPs
- It MUST cite the SOP ID(s) in its response
- It MUST use the actual weather numbers from the API
- If no SOPs matched, it must say "I don't have guidance for that"
- It must NEVER invent generic advice
"""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from app.config import settings
from app.models.state import AgentState


RESPONSE_SYSTEM_PROMPT = """You are a Weather Advisory Support Bot. You help users make safe decisions about outdoor activities based on current weather conditions and company safety policies (SOPs).

CRITICAL RULES — NEVER VIOLATE THESE:
1. Every piece of advice you give MUST come from the matched SOPs provided below. You do NOT get to decide what good advice is.
2. You MUST cite the SOP ID (e.g., "[Per SOP-002]") in your response so we can trace why you said what you said.
3. The weather numbers you mention MUST be the exact numbers from the API data provided. Do NOT round, estimate, or recall different numbers.
4. If no SOPs matched AND the query is about outdoor activity, that means conditions are within safe thresholds — tell the user it looks good. If the query is NOT about outdoor activity at all (e.g., indoor cooking), say kindly that you specialize in outdoor weather safety.
5. Be conversational, empathetic, and helpful — but never at the cost of accuracy.
6. If multiple SOPs apply, address the most severe one first, then mention others.
7. Always mention the location and current conditions so the user knows you checked real data.

TONE: Friendly, clear, safety-conscious. Like a knowledgeable friend who checks the weather for you."""


RESPONSE_WITH_SOPS_PROMPT = """Based on the current weather data and matched safety policies, compose a helpful response.

LOCATION: {location_name} ({country})
{weather_summary}

MATCHED SAFETY POLICIES:
{matched_sops_text}

USER'S QUESTION: "{user_query}"
DETECTED ACTIVITY: "{activity}"

Compose a natural, conversational response that:
1. Acknowledges their question
2. States the relevant weather conditions (using EXACT API numbers)
3. Gives advice from the matched SOP(s), citing each by ID
4. If multiple SOPs apply, address the most severe first
5. Offers practical alternatives if the advice is to avoid the activity
"""


RESPONSE_NO_SOP_PROMPT = """The user asked about outdoor activity safety. I have weather data, and NONE of our safety policies (SOPs) triggered — meaning all weather parameters are within safe thresholds.

LOCATION: {location_name} ({country})
{weather_summary}

USER'S QUESTION: "{user_query}"
DETECTED ACTIVITY: "{activity}"

Important context: Our SOPs define specific dangerous thresholds (e.g., wind > 40 km/h, temp > 35°C, heavy rain > 10mm). Since NONE of these thresholds were crossed, conditions appear safe for the user's activity.

Compose a response that:
1. Acknowledges their question
2. Mentions the current conditions (using EXACT API numbers)
3. Clearly states that based on current weather data, no safety concerns were flagged by our policies — conditions look good for their activity
4. Still adds a brief common-sense reminder (e.g., stay hydrated, carry sunscreen if UV is moderate) but do NOT frame this as a safety warning
5. Keep the tone positive and encouraging
6. Do NOT cite any SOP ID — no SOPs were matched so there is nothing to cite. Do NOT invent fake SOP IDs like "SOP-000"

If the activity is completely unrelated to outdoor/weather (e.g., indoor cooking, studying), then say kindly that you specialize in outdoor activity safety and this question is outside your scope.
"""


async def generate_response_node(state: AgentState) -> dict:
    """Generate the final SOP-grounded response for the user.

    The LLM composes language but is constrained to only use matched SOPs
    and actual API weather data.
    """
    matched_sops = state.get("matched_sops", [])
    weather_summary = state.get("weather_summary", "")
    user_query = state.get("user_query", "")
    activity = state.get("activity", "")
    location = state.get("location", {}) or {}
    location_name = location.get("name", state.get("location_name", "Unknown"))
    country = location.get("country", "")

    llm = ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model_name=settings.MODEL_NAME,
        temperature=0.3,  # Slight creativity for natural language
    )

    messages = [SystemMessage(content=RESPONSE_SYSTEM_PROMPT)]

    # Include conversation history for context
    history = state.get("messages", [])
    if history:
        recent = history[-6:]
        for msg in recent:
            messages.append(msg)

    if matched_sops:
        # Format matched SOPs for the prompt
        sops_text = ""
        for sop in matched_sops:
            sops_text += f"\n[{sop['sop_id']}] {sop['sop_name']} (Severity: {sop['severity']})\n"
            sops_text += f"  Reason triggered: {sop.get('reason', 'N/A')}\n"
            sops_text += f"  Guidance: {sop.get('guidance', 'N/A')}\n"

        prompt = RESPONSE_WITH_SOPS_PROMPT.format(
            location_name=location_name,
            country=country,
            weather_summary=weather_summary,
            matched_sops_text=sops_text,
            user_query=user_query,
            activity=activity,
        )
    else:
        prompt = RESPONSE_NO_SOP_PROMPT.format(
            location_name=location_name,
            country=country,
            weather_summary=weather_summary,
            user_query=user_query,
            activity=activity,
        )

    messages.append(HumanMessage(content=prompt))

    try:
        response = await llm.ainvoke(messages)
        return {
            "response": response.content,
            "messages": [
                HumanMessage(content=user_query),
                AIMessage(content=response.content),
            ],
        }
    except Exception as e:
        error_msg = (
            "I'm sorry, I encountered an error generating a response. "
            "Please try again in a moment."
        )
        return {
            "response": error_msg,
            "messages": [
                HumanMessage(content=user_query),
                AIMessage(content=error_msg),
            ],
            "error": f"Response generation failed: {str(e)}",
        }
