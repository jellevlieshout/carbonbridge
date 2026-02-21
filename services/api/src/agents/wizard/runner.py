"""
Orchestration entrypoint for the buyer wizard.

Usage from the route:
    async for event in run_wizard_turn(session_id, buyer_id):
        yield sse_event(event)

Error handling:
- pydantic_ai.UnexpectedModelBehavior (retry exhaustion, request_limit): recoverable
  → yields a friendly message and keeps the session at the current step.
- pydantic_ai.UsageLimitExceeded: same treatment.
- Any other exception: logs full traceback, yields generic error.
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
    """Yield words with a short delay for a natural streaming feel."""
    words = text.split(" ")
    for i, word in enumerate(words):
        token = word if i == 0 else f" {word}"
        yield token
        await asyncio.sleep(0.03)


# ── recoverable error responses per exception type ────────────────────

_RECOVERABLE_FALLBACK = (
    "I'm having a little trouble thinking right now — "
    "please send your message again and I'll continue from where we left off."
)


def _is_pydantic_ai_retry_error(exc: Exception) -> bool:
    """Return True for Pydantic AI retry-exhaustion and request-limit errors."""
    try:
        from pydantic_ai.exceptions import UnexpectedModelBehavior, UsageLimitExceeded
        return isinstance(exc, (UnexpectedModelBehavior, UsageLimitExceeded))
    except ImportError:
        pass
    # Fallback: match on string representation
    msg = str(exc)
    return (
        "Exceeded maximum ret" in msg
        or "The next request would exceed" in msg
        or "request_limit" in msg
    )


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

    original_step: str = session.data.current_step

    # 2. Get the latest user message
    latest_user_msg = ""
    for msg in reversed(session.data.conversation_history):
        if msg.role == "user":
            latest_user_msg = msg.content
            break

    if not latest_user_msg:
        latest_user_msg = "Hello, I'd like to buy carbon offsets."

    # 3. Hydrate state
    initial_state: WizardState = state_from_session(session, latest_user_msg)

    # 4. Run the LangGraph graph (one node per turn)
    final_state: Optional[WizardState] = None
    response_text = ""
    graph_error = False

    try:
        graph = get_wizard_graph()
        final_state = await graph.ainvoke(initial_state)
    except Exception as exc:
        if _is_pydantic_ai_retry_error(exc):
            logger.warning(
                "Wizard retry/limit error — session=%s step=%s error=%s: %s",
                session_id, original_step, type(exc).__name__, exc,
            )
            response_text = _RECOVERABLE_FALLBACK
        else:
            logger.error(
                "Wizard graph error — session=%s step=%s error=%s: %s",
                session_id, original_step, type(exc).__name__, exc,
                exc_info=True,
            )
            response_text = _RECOVERABLE_FALLBACK
        graph_error = True

    if final_state is not None:
        response_text = final_state.get("response_text") or ""

    if not response_text:
        response_text = _RECOVERABLE_FALLBACK
        graph_error = True

    # 5. Stream response tokens
    full_response = ""
    async for token in _stream_text(response_text):
        full_response += token
        yield _token_event(token)

    # 6. Determine step transition
    new_step: Optional[str] = None
    step_advanced = False

    if final_state is not None:
        new_step = final_state.get("next_step")
        # Ignore internal "complete" / "autobuy_waitlist" as persisted step values
        # — we keep them as signals but don't advance the persisted step to them
        # unless they map to a valid WizardStep literal.
        _valid_steps = {
            "profile_check", "onboarding", "footprint_estimate",
            "preference_elicitation", "listing_search",
            "recommendation", "order_creation",
        }
        if new_step and new_step not in _valid_steps:
            new_step = None  # drop non-persisted step signals
        step_advanced = bool(new_step and new_step != original_step)

    # 7. Emit step_change before done so UI updates progress dots first
    if step_advanced and new_step:
        yield _step_change_event(new_step)

    # 8. Emit done
    yield _done_event(full_response)

    # 9. Persist all updates to Couchbase (best-effort; log on failure)
    try:
        await wizard_session_add_message(session_id, "assistant", full_response)

        if step_advanced and new_step and not graph_error:
            await wizard_session_update_step(session_id, cast(WizardStep, new_step))

        if final_state is not None:
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

            # Persist autonomous-buy handoff intent
            if final_state.get("autobuy_opt_in"):
                context_kwargs["autobuy_opt_in"] = True
                snapshot = final_state.get("autobuy_criteria_snapshot")
                if snapshot:
                    context_kwargs["autobuy_criteria_snapshot"] = snapshot

            search_broadened = final_state.get("search_broadened")
            if search_broadened:
                context_kwargs["search_broadened"] = True

            if context_kwargs:
                await wizard_session_save_context(session_id, **context_kwargs)

    except Exception as exc:
        logger.warning(
            "Failed to persist wizard turn — session=%s step=%s: %s",
            session_id, original_step, exc,
        )
