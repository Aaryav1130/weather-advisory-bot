# 🌤️ Weather Advisory Support Bot

> **MediBuddy Brainwave — AI Product Engineering Internship Assignment**

An AI-powered outdoor activity safety advisor that uses **live weather data** and **Standard Operating Procedures (SOPs)** to give traceable, policy-grounded safety advice. Built with LangGraph, Groq (Llama 3.3 70B), and Streamlit.

## 🎯 What It Does

1. **Takes** a user's question about outdoor activity safety ("Is it safe to cycle in Mumbai today?")
2. **Pulls** live weather data from [Open-Meteo](https://open-meteo.com/) for that location
3. **Matches** the conditions against 10 written safety policies (SOPs)
4. **Responds** with advice that's **traceable to a specific SOP** — never a free-floating guess

**Every answer cites a policy. If no policy applies, the bot says so honestly.**

## 🏗️ Architecture

```
User Input → Extract Intent → Fetch Weather → Match SOPs → Generate Response
                               ↓ (failure)      ↓ (no match)
                           Fallback Node      No-SOP Response
```

- **LangGraph** with 7 nodes and 3 conditional branching points
- **Deterministic** weather/geocoding pipeline (no LLM hallucination of numbers)
- **LLM** for semantic intent extraction, SOP matching, and response composition
- **SOPs in YAML** — add a new policy without touching code

See [docs/design_decisions.md](docs/design_decisions.md) for detailed rationale.

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- A free [Groq API key](https://console.groq.com/) (free tier is sufficient)

### 1. Clone & Install

```bash
git clone https://github.com/Aaryav1130/weather-advisory-bot.git
cd weather-advisory-bot
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your Groq API key:
# GROQ_API_KEY=your_key_here
```

### 3. Run the Backend

```bash
python -m uvicorn app.main:app --reload --port 8000
```

### 4. Run the Frontend (in a new terminal)

```bash
streamlit run frontend/streamlit_app.py
```

The chat UI opens at `http://localhost:8501`

### 5. Run the Eval Suite

```bash
python -m eval.eval_suite
```

## 📋 SOPs (Standard Operating Procedures)

10 policies across 4 categories, stored in [`sops/policies.yaml`](sops/policies.yaml):

| Category | SOPs | Examples |
|----------|------|----------|
| **Outdoor Exercise** | SOP-001 to SOP-004 | UV warning, rain cycling risk, extreme heat, strong wind |
| **Travel Safety** | SOP-005 to SOP-007 | Rain delays, low visibility, severe weather travel ban |
| **Vulnerable Groups** | SOP-008, SOP-009 | Child/elderly heat advisory, pet heat warning |
| **Outdoor Leisure** | SOP-010 | Picnic/leisure comfort (holistic, non-numeric) |

**Format:** YAML — human-readable, machine-parseable, and decoupled from code.

**Why YAML:** A non-technical team member can add an 11th SOP by appending a new block to the YAML file. No code changes required.

## 🧪 Eval Suite

8 test cases covering all required scenarios:

| # | Test | Category | What It Checks |
|---|------|----------|---------------|
| 1 | High Wind Cycling | SOP Applies | SOP-004 triggers for cycling + wind |
| 2 | Heat + Elderly | SOP Applies | SOP-008 triggers for elderly + heat |
| 3 | Paraphrased Picnic | Paraphrase | "Eating lunch in park" → SOP-010 without keywords |
| 4 | Paraphrased Scooter | Paraphrase | "Take my Activa" → two-wheeler SOPs |
| 5 | Severe Weather | Live Data | Real API numbers cited, not generic warnings |
| 6 | Indoor Cooking | No SOP | Bot says "no guidance" — doesn't invent advice |
| 7 | API Down | Failure | Honest failure, no fabricated forecast |
| 8 | Prompt Injection | Adversarial | User tries to override SOPs via injection |

See [`eval/eval_suite.py`](eval/eval_suite.py) for implementation and results.

## 📁 Project Structure

```
weather-advisory-bot/
├── README.md
├── .env.example
├── .gitignore
├── requirements.txt
├── sops/
│   └── policies.yaml          # All 10 SOPs — edit this, not code
├── app/
│   ├── main.py                # FastAPI backend
│   ├── graph.py               # LangGraph agent (the core)
│   ├── config.py              # Environment config
│   ├── models/
│   │   └── state.py           # LangGraph state schema
│   ├── nodes/
│   │   ├── extract_intent.py  # Parse query → location + activity
│   │   ├── fetch_weather.py   # Open-Meteo API calls
│   │   ├── match_sops.py      # Semantic SOP matching
│   │   ├── generate_response.py # SOP-grounded response
│   │   └── fallback.py        # Honest failure handlers
│   └── utils/
│       ├── geocoding.py       # City → lat/long
│       ├── weather_client.py  # Weather API wrapper
│       └── sop_loader.py      # YAML SOP loader
├── frontend/
│   └── streamlit_app.py       # Chat UI
├── eval/
│   └── eval_suite.py          # Automated eval (8 cases)
└── docs/
    └── design_decisions.md    # Architecture rationale
```

## ⚙️ Tech Stack

| Component | Choice | Why |
|-----------|--------|-----|
| Agent Framework | **LangGraph** | Hard requirement; real graph with branching |
| LLM | **Groq + Llama 3.3 70B** | Free, fast, good instruction following |
| Weather API | **Open-Meteo** | Free, no key, reliable |
| Backend | **FastAPI** | Async, fast, production-ready |
| Frontend | **Streamlit** | Fastest to build, built-in chat UI |
| SOPs | **YAML** | Human-readable, code-decoupled |

## 📝 Trade-offs & Notes

- **Live weather dependency:** Eval cases that check for severe conditions depend on actual weather at query time. In production, we'd mock the API for deterministic testing.
- **Single-session memory:** Memory resets between sessions per assignment spec. For production, we'd add Redis or a database.
- **No auth:** The deployed version has no authentication. In production, we'd add user auth and rate limiting.
- **Groq rate limits:** Free tier has rate limits. For production, we'd add retry logic and queue management.

## 📄 License

This project was built as an assessment for the MediBuddy Brainwave AI Product Engineering Internship.
