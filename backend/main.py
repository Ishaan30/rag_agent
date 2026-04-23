"""
RAG Chatbot — Main Application
FastAPI app that wires together the chat, RAG, and agent endpoints.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from routers import chat, documents

app = FastAPI(
    title="RAG Chatbot API",
    description="Conversational AI with RAG and agent capabilities",
    version="1.0.0",
)

# Allow the frontend (served separately or from the same origin) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])

# Serve the static frontend
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Serve the main HTML frontend."""
    return FileResponse(os.path.join(frontend_dir, "index.html"))


@app.get("/health")
async def health_check():
    return {"status": "ok"}