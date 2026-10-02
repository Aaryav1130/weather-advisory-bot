# Design Decisions

This document explains the key architectural and design decisions made in building the Weather Advisory Support Bot.

## 1. SOP Format: YAML

**Decision:** Store SOPs in a YAML file (`sops/policies.yaml`), separate from application code.

**Why:** 
- YAML is human-readable — non-technical policy writers can edit it
- Machine-parseable — the system loads it dynamically at startup
- Adding an 11th SOP requires zero code changes — just append a YAML block
- Version-controllable — changes are tracked in git diffs
- This was a non-negotiable requirement: *"Adding or changing a policy must not require touching the code that fetches weather or calls the model."*

**Trade-offs:**
- YAML doesn't support complex conditional logic natively — the "holistic" SOP (SOP-010) uses a description field that the LLM interprets
- No runtime validation of SOP schema (would add Pydantic models for production)

## 2. LLM for SOP Matching (Not Keyword/String Lookup)

**Decision:** Use the LLM (Groq Llama 3.3 70B) for semantic SOP matching instead of keyword matching.

**Why:**
- Users paraphrase questions — "Can I take my Activa to work?" should match two-wheeler SOPs even though "Activa" isn't a keyword
- The assignment explicitly tests for this: *"At least 2 cases are phrased so they don't reuse your SOP's wording"*
- Keyword matching would fail on novel phrasings, slang, and context-dependent queries

**What's deterministic vs. LLM:**
- **Deterministic (code):** Weather API calls, geocoding, data formatting, routing logic
- **LLM:** Intent extraction, SOP matching, response composition
- **Key constraint:** The LLM never decides facts. All numbers come from the API.

## 3. Graph Architecture: 7 Nodes, 3 Branching Points

**Decision:** A LangGraph `StateGraph` with 7 nodes and conditional edges at 3 decision points.

**Why this structure:**
```
extract_intent → fetch_weather → [BRANCH: location/API success?]
                                 ├── handle_no_location → END
                                 ├── handle_geocoding_failure → END
                                 ├── handle_weather_api_failure → END
                                 └── match_sops → [BRANCH: SOPs matched?]
                                                   └── generate_response → END
```

- **Real branching, not a single chain:** The failure paths are first-class graph nodes, not try/catch blocks hidden in one function
- **Each node has a single responsibility:** Extract intent, fetch weather, match SOPs, generate response, handle specific failures
- **Failure modes are explicit:** Each failure type gets its own node with a tailored honest response

**Trade-offs:**
- Could add more nodes (e.g., separate geocoding node) — kept it simple to avoid over-engineering
- The `match_sops` → `generate_response` edge is always taken (both matched and unmatched cases) — the generate_response node handles the "no SOP" case with a different prompt

## 4. Multi-SOP Conflict Resolution: Rank by Severity

**Decision:** When multiple SOPs match, surface ALL of them but rank by severity (critical > high > moderate > advisory).

**Why:**
- A user asking "should I cycle today?" when there's both high UV AND strong wind needs to know about BOTH risks
- The most dangerous condition is addressed first in the response
- The assignment says *"Pick one and answer with only that SOP, surface both, rank by severity — whatever you decide, but decide on purpose"*

## 5. Session Memory: LangGraph Message History

**Decision:** Use LangGraph's built-in `add_messages` reducer for session memory. Message history is stored in-memory on the server, keyed by session ID.

**Why:**
- Natural fit with LangGraph's state management
- Follow-up questions like "what about this evening?" get context from earlier turns
- Memory resets between sessions (per assignment spec — no cross-session persistence)
- Simple in-memory dict is sufficient; no need for Redis/database for this use case

## 6. LLM Choice: Groq + Llama 3.3 70B

**Decision:** Use Groq's free API with the Llama 3.3 70B Versatile model.

**Why:**
- 100% free with generous rate limits
- Extremely fast inference (Groq's LPU architecture)
- Llama 3.3 70B is capable enough for structured tasks (JSON extraction, policy matching)
- Good instruction following for staying grounded in SOPs

## 7. Frontend: Streamlit

**Decision:** Minimal Streamlit chat UI instead of a custom React app.

**Why:**
- Assignment says: *"We're not grading design or polish. We're grading whether it runs, whether a reviewer can type into it, and whether a reply comes back."*
- Streamlit's `st.chat_message` and `st.chat_input` give us a clean chat UI in ~100 lines
- Debug mode shows matched SOPs, weather data, and location — useful for the review call
- Saved hours that were better spent on the graph and eval suite

## 8. Weather Data Pipeline: Deterministic, No LLM Involvement

**Decision:** The entire weather data pipeline (geocoding → API call → data formatting) is deterministic Python code with no LLM involvement.

**Why:**
- The assignment non-negotiable: *"Numbers it reports back must be the numbers that actually came from the API"*
- If we let the LLM participate in the data pipeline, it could hallucinate or estimate numbers
- The formatted weather summary is passed to the LLM as context, but the LLM doesn't get to modify or interpret the raw data
