"""
🌤️ Weather Advisory Support Bot
A safety-first outdoor activity advisor powered by live weather data and SOPs.
Built for the MediBuddy Brainwave AI Product Engineering Internship.
"""

import uuid
import requests
import streamlit as st

# --- Page Config ---
st.set_page_config(
    page_title="Weather Advisory Bot",
    page_icon="🌤️",
    layout="centered",
)

# --- Constants ---
API_URL = "http://localhost:8001"

# --- Session State ---
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "debug_info" not in st.session_state:
    st.session_state.debug_info = []


# --- Header ---
st.title("🌤️ Weather Advisory Bot")
st.caption(
    "Ask me about outdoor activity safety anywhere in the world. "
    "I use live weather data and official safety policies (SOPs) to give you accurate advice."
)

# --- Sidebar ---
with st.sidebar:
    st.header("ℹ️ About")
    st.markdown(
        """
        This bot answers questions about outdoor activity safety
        using **live weather data** from [Open-Meteo](https://open-meteo.com/)
        and **Standard Operating Procedures (SOPs)**.

        **Every answer is traceable** to a specific policy — the bot
        never invents advice.

        ---
        **Example questions:**
        - *Is it safe to cycle in Mumbai today?*
        - *Can I take my dog for a walk in Delhi?*
        - *Is today good for a picnic in Bangalore?*
        - *Should I drive to Pune right now?*
        - *Can my elderly mother go for a walk in Chennai?*
        ---
        """
    )

    if st.button("🔄 New Conversation"):
        # Reset session
        try:
            requests.post(f"{API_URL}/reset/{st.session_state.session_id}")
        except Exception:
            pass
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state.debug_info = []
        st.rerun()

    show_debug = st.checkbox("Show debug info", value=False)


# --- Chat History ---
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

    # Show debug info if enabled
    if show_debug and msg["role"] == "assistant" and i < len(st.session_state.debug_info):
        debug = st.session_state.debug_info[i]
        if debug:
            with st.expander("🔍 Debug Info"):
                if debug.get("location"):
                    loc = debug["location"]
                    st.write(f"📍 **Location:** {loc.get('name', 'N/A')} ({loc.get('country', '')})")
                    st.write(f"   Lat: {loc.get('latitude', 'N/A')}, Lon: {loc.get('longitude', 'N/A')}")

                if debug.get("weather_summary"):
                    st.code(debug["weather_summary"], language="text")

                if debug.get("matched_sops"):
                    st.write("**Matched SOPs:**")
                    for sop in debug["matched_sops"]:
                        severity_colors = {
                            "critical": "🔴",
                            "high": "🟠",
                            "moderate": "🟡",
                            "advisory": "🟢",
                        }
                        emoji = severity_colors.get(sop.get("severity", ""), "⚪")
                        st.write(
                            f"  {emoji} **{sop.get('sop_id', 'N/A')}** — "
                            f"{sop.get('sop_name', 'N/A')} ({sop.get('severity', 'N/A')})"
                        )
                        st.write(f"     Reason: {sop.get('reason', 'N/A')}")
                else:
                    st.write("**No SOPs matched** — response is a no-guidance acknowledgment.")

                if debug.get("error"):
                    st.error(f"Error: {debug['error']}")


# --- Chat Input ---
if user_input := st.chat_input("Ask about outdoor activity safety..."):
    # Display user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Send to backend
    with st.chat_message("assistant"):
        with st.spinner("Checking weather conditions and safety policies..."):
            try:
                response = requests.post(
                    f"{API_URL}/chat",
                    json={
                        "message": user_input,
                        "session_id": st.session_state.session_id,
                    },
                    timeout=30,
                )

                if response.status_code == 200:
                    data = response.json()
                    bot_response = data.get("response", "Sorry, something went wrong.")
                    st.markdown(bot_response)

                    # Save to history
                    st.session_state.messages.append(
                        {"role": "assistant", "content": bot_response}
                    )

                    # Save debug info
                    st.session_state.debug_info.append(
                        {
                            "location": data.get("location"),
                            "weather_summary": data.get("weather_summary", ""),
                            "matched_sops": data.get("matched_sops", []),
                            "error": data.get("error", ""),
                        }
                    )
                    # Pad debug_info for user messages
                    while len(st.session_state.debug_info) < len(st.session_state.messages):
                        st.session_state.debug_info.insert(
                            len(st.session_state.debug_info) - 1, None
                        )
                else:
                    error_msg = "⚠️ Server returned an error. Please try again."
                    st.error(error_msg)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": error_msg}
                    )
                    st.session_state.debug_info.append(None)

            except requests.exceptions.ConnectionError:
                error_msg = (
                    "⚠️ Cannot connect to the backend server. "
                    "Make sure the FastAPI server is running with: "
                    "`python -m uvicorn app.main:app --reload`"
                )
                st.error(error_msg)
                st.session_state.messages.append(
                    {"role": "assistant", "content": error_msg}
                )
                st.session_state.debug_info.append(None)

            except requests.exceptions.Timeout:
                error_msg = "⚠️ Request timed out. The server might be overloaded. Please try again."
                st.error(error_msg)
                st.session_state.messages.append(
                    {"role": "assistant", "content": error_msg}
                )
                st.session_state.debug_info.append(None)
