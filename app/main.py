"""FastAPI application entry point for Delivery Support Chatbot."""

import os
import mimetypes
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse

# Ensure standard MIME types on Windows
mimetypes.add_type("text/html", ".html")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("application/json", ".json")

from app.models import ChatRequest, ChatResponse, HealthResponse
from app.agent import DeliverySupportAgent
from app.db import ORDERS_DB

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="SwiftDrop GenAI Delivery Support Bot",
    description="Intelligent delivery customer support chatbot powered by Google Gemini & Native Function Calling.",
    version="1.0.0"
)

# Enable CORS for external frontend or Render hosting
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Agent with active credentials
agent = DeliverySupportAgent()

# Mount static files
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_index():
    """Serve the single-page chat application."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Delivery Support Chatbot API is running</h1><p>Static UI not found.</p>")


@app.get("/api/status", tags=["Status"])
async def get_status():
    """Returns whether live Gemini LLM is active or in preview mode."""
    is_live = bool(agent.client)
    return {
        "is_live": is_live,
        "model": agent.model_name if is_live else "Offline Preview Engine",
        "has_api_key": bool(agent.api_key and agent.api_key != "your_gemini_api_key_here")
    }


@app.get("/healthz", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint for Render.com monitoring."""
    return HealthResponse(
        status="healthy",
        service="delivery-support-chatbot",
        version="1.0.0"
    )


@app.post("/api/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_endpoint(request: ChatRequest):
    """Process incoming chat query with Gemini Native Tool Calling."""
    try:
        reply_text, tool_calls = agent.run_chat(
            user_message=request.message,
            history=request.history or []
        )
        return ChatResponse(
            response=reply_text,
            tool_calls=tool_calls,
            status="success"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


@app.get("/api/orders", tags=["Orders"])
async def list_orders():
    """Get active orders in the database (useful for frontend test pills)."""
    return {
        "orders": list(ORDERS_DB.values())
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
