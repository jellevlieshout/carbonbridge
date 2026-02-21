import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from models.operations.wizard_sessions import (
    wizard_session_create,
    wizard_session_get,
    wizard_session_get_active_for_buyer,
    wizard_session_add_message,
)
from utils import log
from .dependencies import require_authenticated

logger = log.get_logger(__name__)

router = APIRouter(prefix="/wizard", tags=["wizard"])


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------

def _session_to_dict(session) -> dict:
    return {
        "id": session.id,
        "data": session.data.model_dump(mode="json"),
    }


def _sse_event(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


# ---------------------------------------------------------------------------
# POST /wizard/session — create or resume session
# ---------------------------------------------------------------------------

@router.post("/session")
async def route_wizard_session_create(user: dict = Depends(require_authenticated)):
    buyer_id = user["sub"]

    # Return existing active session if one exists
    existing = await wizard_session_get_active_for_buyer(buyer_id)
    if existing:
        return _session_to_dict(existing)

    session = await wizard_session_create(buyer_id)
    return _session_to_dict(session)


# ---------------------------------------------------------------------------
# POST /wizard/session/{id}/message — send a user message
# ---------------------------------------------------------------------------

class MessageRequest(BaseModel):
    content: str


@router.post("/session/{session_id}/message")
async def route_wizard_send_message(
    session_id: str,
    body: MessageRequest,
    user: dict = Depends(require_authenticated),
):
    session = await wizard_session_get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.data.buyer_id != user["sub"]:
        raise HTTPException(status_code=403, detail="Not your session")

    # Persist user message
    updated = await wizard_session_add_message(session_id, "user", body.content)
    return _session_to_dict(updated)


# ---------------------------------------------------------------------------
# GET /wizard/session/{id}/stream — SSE streaming response
# ---------------------------------------------------------------------------

# Placeholder responses until Pydantic AI agent is wired up
PLACEHOLDER_RESPONSES = {
    "profile_check": (
        "Welcome to CarbonBridge! I'm here to help you find the right carbon "
        "credits for your business. Let me start by learning a bit about your "
        "company. What sector does your business operate in, and roughly how "
        "many employees do you have?"
    ),
    "onboarding": (
        "Great, thanks for sharing that. I'll use this to estimate your "
        "carbon footprint and find credits that match your needs. "
        "Shall we look at your estimated emissions next?"
    ),
    "footprint_estimate": (
        "Based on what you've told me, I've estimated your annual carbon "
        "footprint. Now let's talk about what kind of offset projects "
        "appeal to you — do you have a preference for forestry, renewable "
        "energy, cookstoves, or another type?"
    ),
    "preference_elicitation": (
        "Noted! I'll focus on projects matching those preferences. "
        "Let me search our verified listings for the best options. "
        "Give me just a moment..."
    ),
    "listing_search": (
        "I've found several verified listings that match your criteria. "
        "Let me put together a recommendation for you."
    ),
    "recommendation": (
        "Here are my top recommendations based on your preferences and "
        "budget. Take a look and let me know if you'd like to proceed "
        "with any of these, or if you'd like me to search again with "
        "different criteria."
    ),
    "order_creation": (
        "Excellent choice! I'll set up your order now. "
        "You'll see a summary with the total cost before confirming."
    ),
}


async def _stream_placeholder(session):
    """Stream a placeholder response token-by-token via SSE."""
    step = session.data.current_step
    text = PLACEHOLDER_RESPONSES.get(step, PLACEHOLDER_RESPONSES["profile_check"])

    # Stream tokens (word by word for natural feel)
    words = text.split(" ")
    full_response = ""
    for i, word in enumerate(words):
        token = word if i == 0 else f" {word}"
        full_response += token
        yield _sse_event({"type": "token", "content": token})
        await asyncio.sleep(0.04)

    # Persist assistant response
    await wizard_session_add_message(session.id, "assistant", full_response)

    # Send done event
    yield _sse_event({"type": "done", "full_response": full_response})
    yield "data: [DONE]\n\n"


@router.get("/session/{session_id}/stream")
async def route_wizard_stream(
    session_id: str,
    user: dict = Depends(require_authenticated),
):
    session = await wizard_session_get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.data.buyer_id != user["sub"]:
        raise HTTPException(status_code=403, detail="Not your session")

    return StreamingResponse(
        _stream_placeholder(session),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
