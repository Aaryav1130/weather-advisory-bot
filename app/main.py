"""FastAPI backend for the Weather Advisory Bot.

Provides a REST API endpoint for the Streamlit frontend to communicate with
the LangGraph agent. Also serves as the entry point for deployment.
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import settings
from app.graph import agent


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Validate configuration on startup."""
    settings.validate()
    print("✅ Weather Advisory Bot started successfully!")
    print(f"   Model: {settings.MODEL_NAME}")
    print(f"   Weather API: {settings.WEATHER_API_URL}")
    yield
    print("👋 Weather Advisory Bot shutting down.")


app = FastAPI(
    title="Weather Advisory Support Bot",
    description="AI-powered outdoor activity safety advisor using live weather data and SOPs",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    """Incoming chat message from the user."""
    message: str
    session_id: str = "default"


class ChatResponse(BaseModel):
    """Bot's response to the user."""
    response: str
    matched_sops: list[dict] = []
    location: dict | None = None
    weather_summary: str = ""
    error: str = ""


# In-memory session store (resets on restart — per assignment spec)
sessions: dict[str, list] = {}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process a user message through the LangGraph agent.

    Maintains session memory within a single chat session (per assignment spec).
    Memory resets between sessions / server restarts.
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Get or create session message history
    session_messages = sessions.get(request.session_id, [])

    try:
        # Run the LangGraph agent
        result = await agent.ainvoke({
            "user_query": request.message,
            "messages": session_messages,
            "location_name": "",
            "activity": "",
            "location": None,
            "weather_data": None,
            "weather_summary": "",
            "matched_sops": [],
            "response": "",
            "error": "",
        })

        # Update session history
        sessions[request.session_id] = result.get("messages", [])

        return ChatResponse(
            response=result.get("response", "Sorry, something went wrong."),
            matched_sops=result.get("matched_sops", []),
            location=result.get("location"),
            weather_summary=result.get("weather_summary", ""),
            error=result.get("error", ""),
        )

    except Exception as e:
        return ChatResponse(
            response=(
                "I'm sorry, I encountered an unexpected error processing your request. "
                "Please try again in a moment."
            ),
            error=str(e),
        )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "model": settings.MODEL_NAME}


@app.post("/reset/{session_id}")
async def reset_session(session_id: str):
    """Reset a chat session's memory."""
    if session_id in sessions:
        del sessions[session_id]
    return {"status": "session_reset", "session_id": session_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
