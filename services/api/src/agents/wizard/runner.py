"""
Orchestration entrypoint for the buyer wizard.

Usage from the route:
    async for event in run_wizard_turn(session_id, buyer_id):
        yield sse_event(event)

Responsibilities:
1. Load WizardSession from Couchbase.
2. Hydrate WizardState from persisted data + latest user message.
3. Run the LangGraph graph (single step — one LLM call per turn).
4. Persist updated step, preferences, and context back to Couchbase.
5. Yield SSE-compatible event dicts token-by-token + step_change + done.
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator, Dict, Optional, cast

from models.entities.couchbase.wizard_sessions import WizardStep

from models.operations.wizard_sessions import (
    wizard_session_add_message,
    wizard_session_get,
    wizard_session_save_context,
    wizard_session_update_preferences,
    wizard_session_update_step,
)
from utils import log
from .graph import get_wizard_graph
from .state import WizardState, state_from_session

logger = log.get_logger(__name__)

# ── SSE event constructors ────────────────────────────────────────────


def _token_event(content: str) -> Dict[str, Any]:
    return {"type": "token", "content": content}


def _step_change_event(step: str) -> Dict[str, Any]:
    return {"type": "step_change", "step": step}


def _done_event(full_response: str) -> Dict[str, Any]:
    return {"type": "done", "full_response": full_response}


def _error_event(message: str) -> Dict[str, Any]:
    return {"type": "error", "message": message}


# ── token streamer ────────────────────────────────────────────────────


async def _stream_text(text: str) -> AsyncGenerator[str, None]:
    """
    Yield words one at a time with a small delay for a natural streaming feel.
    Can be replaced with real Pydantic AI token streaming (agent.run_stream())
    for true per-token delivery.
    """
    words = text.split(" ")
    for i, word in enumerate(words):
        token = word if i == 0 else f" {word}"
        yield token
        await asyncio.sleep(0.03)


# ── main entrypoint ───────────────────────────────────────────────────


async def run_wizard_turn(
    session_id: str,
    buyer_id: str,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Run one wizard turn and yield SSE event dicts.

    Expects the user message to have already been persisted to the session
    by POST /wizard/session/{id}/message before this generator is consumed.
    """
    # 1. Load session
    session = await wizard_session_get(session_id)
    if not session:
        yield _error_event("Session not found")
        return

    # 2. Get the latest user message from persisted history
    latest_user_msg = ""
    for msg in reversed(session.data.conversation_history):
        if msg.role == "user":
            latest_user_msg = msg.content
            break

    if not latest_user_msg:
        # First-turn auto-kick
        latest_user_msg = "Hello, I'd like to buy carbon offsets."

    # 3. Hydrate state
    initial_state: WizardState = state_from_session(session, latest_user_msg)

    # 4. Run the LangGraph graph (one node per turn)
    try:
        graph = get_wizard_graph()
        final_state: WizardState = await graph.ainvoke(initial_state)
    except Exception as exc:
        logger.error("Wizard graph error for session %s: %s", session_id, exc)
        yield _error_event("I hit a technical snag. Please try again in a moment.")
        return

    # 5. Extract results from the final state dict
    response_text: str = final_state.get("response_text") or ""
    new_step: Optional[str] = final_state.get("next_step")
    original_step: str = session.data.current_step
    step_advanced = bool(new_step and new_step != original_step)

    # 6. Stream response tokens
    full_response = ""
    async for token in _stream_text(response_text):
        full_response += token
        yield _token_event(token)

    # 7. Emit step_change before done (UI updates progress dots first)
    if step_advanced and new_step:
        yield _step_change_event(new_step)

    # 8. Emit done
    yield _done_event(full_response)

    # 9. Persist all updates to Couchbase
    try:
        await wizard_session_add_message(session_id, "assistant", full_response)

        if step_advanced and new_step:
            await wizard_session_update_step(session_id, cast(WizardStep, new_step))

        new_prefs = final_state.get("extracted_preferences")
        if new_prefs:
            await wizard_session_update_preferences(session_id, new_prefs)

        context_kwargs: Dict[str, Any] = {}
        footprint = final_state.get("footprint_estimate")
        if footprint:
            context_kwargs["footprint_context"] = footprint
        listings = final_state.get("recommended_listings") or []
        if listings:
            context_kwargs["recommended_listing_ids"] = [
                item.get("id") for item in listings if item.get("id")
            ]
        draft_id = final_state.get("draft_order_id")
        if draft_id:
            context_kwargs["draft_order_id"] = draft_id
        draft_total = final_state.get("draft_order_total_eur")
        if draft_total is not None:
            context_kwargs["draft_order_total_eur"] = draft_total
        if context_kwargs:
            await wizard_session_save_context(session_id, **context_kwargs)

    except Exception as exc:
        logger.warning(
            "Failed to persist wizard turn for session %s: %s", session_id, exc
        )
