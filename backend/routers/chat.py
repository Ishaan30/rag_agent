"""
Chat Router
Exposes:
  POST /api/chat/message  — stream a response for a given session
  DELETE /api/chat/{session_id}  — clear conversation history
"""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services.agent import stream_agent_response, clear_session

router = APIRouter()


class ChatRequest(BaseModel):
    session_id: str    # Unique ID per browser tab / conversation
    message: str


@router.post("/message")
async def chat_message(req: ChatRequest):
    """
    Stream an AI response for the given message.
    Uses Server-Sent Events (text/event-stream) so the frontend
    can display tokens as they arrive.
    """
    async def token_generator():
        async for token in stream_agent_response(req.session_id, req.message):
            # SSE format: each chunk prefixed with "data: " and ended with double newline
            yield f"data: {token}\n\n"
        # Signal the frontend that the stream is complete
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        token_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",    # Disable Nginx buffering if behind a proxy
        },
    )


@router.delete("/{session_id}")
async def clear_chat(session_id: str):
    """Clear the conversation history for a session."""
    clear_session(session_id)
    return {"message": "Conversation cleared."}