"""
🌤️ Weather Advisory Support Bot
A safety-first outdoor activity advisor powered by live weather data and SOPs.
Built by Aaryav for the MediBuddy Brainwave AI Product Engineering Internship.
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

# --- Custom CSS to make it unique ---
st.markdown("""
    <style>
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Reduce top paddings to pull content up */
    .block-container {
        padding-top: 2rem !important;
    }
    section[data-testid="stSidebar"] > div {
        padding-top: 1rem !important;
    }
    
    /* Adjust sidebar emoji margin */
    .sidebar-emoji {
        text-align: center; 
        font-size: 4rem; 
        margin-top: -2rem;
        margin-bottom: -1rem;
    }
    
    /* Custom Title */
    .custom-title {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        color: #1e3a8a;
        font-weight: 800;
        font-size: 2.8rem;
        margin-top: -2rem;
        margin-bottom: 1rem;
    }
    
    /* Custom button styling */
    .stButton>button {
        background-color: #f8fafc;
        color: #0f172a;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        background-color: #f1f5f9;
        border-color: #94a3b8;
        transform: scale(1.02);
    }
    </style>
""", unsafe_allow_html=True)

# --- Constants ---
API_URL = "http://localhost:8001"
BOT_AVATAR = "🌤️"
USER_AVATAR = "👤"

# --- Session State ---
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "debug_info" not in st.session_state:
    st.session_state.debug_info = []


# --- Header ---
st.markdown('<h1 class="custom-title">Weather Advisory Bot</h1>', unsafe_allow_html=True)

st.markdown(
    "Ask me about outdoor activity safety anywhere in the world. "
    "I use live weather data and official safety policies (SOPs) to give you accurate advice."
)
st.divider()

# --- Sidebar ---
with st.sidebar:
    st.markdown('<div class="sidebar-emoji">⛅🌦️</div>', unsafe_allow_html=True)
    st.header("Project Details")
    st.markdown(
        """
        This agent evaluates outdoor activity safety using:
        - **Live Open-Meteo Data** (Geocoding & Forecast)
        - **10 Custom SOPs** (Standard Operating Procedures)
        - **LangGraph** (Stateful Agent Architecture)
        
        Every answer is strictly grounded in an SOP policy — it will never hallucinate safety advice.

        ---
        **Test Queries:**
        - *Is it safe to cycle in Mumbai today?*
        - *Can I take my dog for a walk in Delhi?*
        - *Is today good for a picnic in Bangalore?*
        - *Should I drive to Pune right now?*
        - *Can my elderly mother go for a walk in Chennai?*
        ---
        """
    )

    if st.button("🔄 Start Fresh Conversation", use_container_width=True):
        # Reset session
        try:
            requests.post(f"{API_URL}/reset/{st.session_state.session_id}")
        except Exception:
            pass
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state.debug_info = []
        st.rerun()

    show_debug = st.checkbox("🐞 Enable Developer Debug Mode", value=False)


# --- Chat History ---
for i, msg in enumerate(st.session_state.messages):
    avatar = USER_AVATAR if msg["role"] == "user" else BOT_AVATAR
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

    # Show debug info if enabled
    if show_debug and msg["role"] == "assistant" and i < len(st.session_state.debug_info):
        debug = st.session_state.debug_info[i]
        if debug:
            with st.expander("🔍 Policy & Weather Context Data"):
                if debug.get("location"):
                    loc = debug["location"]
                    st.write(f"📍 **Location resolved:** {loc.get('name', 'N/A')} ({loc.get('country', '')})")
                    st.caption(f"Coordinates: {loc.get('latitude', 'N/A')}, {loc.get('longitude', 'N/A')}")

                if debug.get("weather_summary"):
                    st.text(debug["weather_summary"])

                if debug.get("matched_sops"):
                    st.write("**Triggered SOPs:**")
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
                        st.write(f"     *Trigger logic:* {sop.get('reason', 'N/A')}")
                else:
                    st.write("**No SOPs matched** — triggering fallback response.")

                if debug.get("error"):
                    st.error(f"Error trace: {debug['error']}")


# --- Chat Input ---
if user_input := st.chat_input("Enter your location and activity..."):
    # Display user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(user_input)

    # Send to backend
    with st.chat_message("assistant", avatar=BOT_AVATAR):
        with st.spinner("Analyzing weather and scanning policies..."):
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
                    error_msg = "⚠️ Server returned an error. Please check backend logs."
                    st.error(error_msg)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": error_msg}
                    )
                    st.session_state.debug_info.append(None)

            except requests.exceptions.ConnectionError:
                error_msg = (
                    "⚠️ Connection refused. "
                    "Make sure the FastAPI backend is running on port 8001: "
                    "`python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload`"
                )
                st.error(error_msg)
                st.session_state.messages.append(
                    {"role": "assistant", "content": error_msg}
                )
                st.session_state.debug_info.append(None)

            except requests.exceptions.Timeout:
                error_msg = "⚠️ Request timed out. The LLM might be taking too long to respond."
                st.error(error_msg)
                st.session_state.messages.append(
                    {"role": "assistant", "content": error_msg}
                )
                st.session_state.debug_info.append(None)

