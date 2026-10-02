"""SOP matching node — determines which policies apply to the current situation.

This node uses the LLM for semantic matching because:
1. Users phrase questions in varied natural language (paraphrases, not keywords)
2. Some SOPs are fuzzy/non-numeric (e.g., "is today good for a picnic?")
3. The match needs to consider both the weather data AND the user's intent

However, the LLM does NOT decide what advice to give — it only identifies
which written SOPs apply. The actual advice comes from the SOP guidance text.
"""

import json

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from app.config import settings
from app.models.state import AgentState
from app.utils.sop_loader import load_sops, format_sops_for_prompt


SOP_MATCHING_PROMPT = """You are a policy-matching engine. Your ONLY job is to determine which Standard Operating Procedures (SOPs) apply to the current situation based on:
1. The user's question and intended activity
2. The current weather data from the API

RULES:
- Match SOPs based on their conditions and the actual weather numbers provided.
- For numeric SOPs: check if the weather data meets the threshold conditions.
- For the holistic SOP (SOP-010): evaluate the overall combination of weather factors.
- Consider activity keywords — an SOP only applies if the user's activity is relevant to it.
- If MULTIPLE SOPs apply, include ALL of them.
- If NO SOPs apply, return an empty list.
- NEVER invent an SOP that doesn't exist in the list below.
- Base your matching ONLY on the SOPs and weather data provided.

{sops_text}

{weather_data}

User's question: "{user_query}"
Detected activity: "{activity}"
Location: "{location_name}"

Respond with ONLY a JSON array of matched SOPs. For each match, include:
- "sop_id": The SOP ID (e.g., "SOP-001")
- "sop_name": The SOP name
- "category": The SOP category
- "severity": The SOP severity level
- "reason": Brief explanation of WHY this SOP was triggered (cite the specific numbers)

If no SOPs match, respond with: []

Output ONLY valid JSON, no other text.
"""


async def match_sops_node(state: AgentState) -> dict:
    """Match current conditions against all SOPs using the LLM.

    The LLM identifies which policies apply based on weather data + user intent.
    It does NOT generate advice — it only returns which SOPs matched and why.
    """
    weather_data = state.get("weather_data")
    weather_summary = state.get("weather_summary", "")
    user_query = state.get("user_query", "")
    activity = state.get("activity", "")
    location_name = state.get("location_name", "")

    # Load SOPs dynamically (supports adding new SOPs without code changes)
    try:
        sops = load_sops()
    except FileNotFoundError:
        return {
            "matched_sops": [],
            "error": "SOPs file not found",
        }

    sops_text = format_sops_for_prompt(sops)

    llm = ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model_name=settings.MODEL_NAME,
        temperature=0,  # Deterministic matching
    )

    prompt = SOP_MATCHING_PROMPT.format(
        sops_text=sops_text,
        weather_data=weather_summary,
        user_query=user_query,
        activity=activity,
        location_name=location_name,
    )

    try:
        response = await llm.ainvoke([
            SystemMessage(content="You are a precise policy-matching engine. Output ONLY valid JSON."),
            HumanMessage(content=prompt),
        ])

        content = response.content.strip()

        # Parse JSON from response (handle markdown code blocks)
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        matched = json.loads(content)

        if not isinstance(matched, list):
            matched = []

        # Validate that matched SOPs actually exist
        valid_ids = {sop["id"] for sop in sops}
        validated_matches = []
        for match in matched:
            if match.get("sop_id") in valid_ids:
                # Enrich with guidance from the actual SOP
                sop = next(s for s in sops if s["id"] == match["sop_id"])
                match["guidance"] = sop.get("guidance", "").strip()
                validated_matches.append(match)

        # Sort by severity: critical > high > moderate > advisory
        severity_order = {"critical": 0, "high": 1, "moderate": 2, "advisory": 3}
        validated_matches.sort(
            key=lambda x: severity_order.get(x.get("severity", "advisory"), 4)
        )

        return {
            "matched_sops": validated_matches,
            "error": "",
        }

    except json.JSONDecodeError:
        return {
            "matched_sops": [],
            "error": "",
        }
    except Exception as e:
        return {
            "matched_sops": [],
            "error": f"SOP matching failed: {str(e)}",
        }
