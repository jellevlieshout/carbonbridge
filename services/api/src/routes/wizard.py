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

    existing = await wizard_session_get_active_for_buyer(buyer_id)
    if existing:
        return _session_to_dict(existing)

    session = await wizard_session_create(buyer_id)
    return _session_to_dict(session)


# ---------------------------------------------------------------------------
# POST /wizard/session/{id}/message — persist user message, then SSE
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

    updated = await wizard_session_add_message(session_id, "user", body.content)
    return _session_to_dict(updated)


# ---------------------------------------------------------------------------
# GET /wizard/session/{id}/stream — SSE streaming response (real agent)
# ---------------------------------------------------------------------------

async def _stream_agent(session_id: str, buyer_id: str):
    """
    Drive the wizard agent and yield SSE-formatted events.
    Imports runner lazily so startup import errors don't break the whole API.
    """
    try:
        from agents.wizard.runner import run_wizard_turn
    except Exception as exc:
        logger.error("Failed to import wizard agent: %s", exc)
        yield _sse_event({"type": "error", "message": "Agent not available"})
        yield "data: [DONE]\n\n"
        return

    try:
        async for event in run_wizard_turn(session_id, buyer_id):
            yield _sse_event(event)
    except Exception as exc:
        logger.error("Wizard stream error for session %s: %s", session_id, exc)
        yield _sse_event({"type": "error", "message": "Unexpected error during generation"})

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
        _stream_agent(session_id, user["sub"]),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
