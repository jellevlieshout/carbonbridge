"""
Orchestration entrypoint for the buyer wizard.

Usage from the route:
    async for event in run_wizard_turn(session_id, buyer_id):
        yield sse_event(event)

Post-turn side effects (after streaming):
1. Persist conversation message, step, preferences, and context.
2. If handoff_to_buyer_agent: call buyer agent and stream outcome.
3. If waitlist_opted_in: enable autonomous agent on user profile + try immediate run.

Error handling:
- pydantic_ai.UnexpectedModelBehavior / UsageLimitExceeded: recoverable
  → yields a friendly message and keeps the session at the current step.
- Any other exception: logs full traceback, yields generic error.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, AsyncGenerator, Dict, Optional, cast

from models.entities.couchbase.wizard_sessions import WizardStep
from models.operations.wizard_sessions import (
    wizard_session_add_message,
    wizard_session_get,
    wizard_session_save_context,
    wizard_session_update_preferences,
    wizard_session_update_step,
)
from utils import log

if TYPE_CHECKING:
    from .schemas import BuyerHandoffResult

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


def _buyer_handoff_event(outcome: str, message: str) -> Dict[str, Any]:
    return {"type": "buyer_handoff", "outcome": outcome, "message": message}


def _waitlist_event(opted_in: bool) -> Dict[str, Any]:
    return {"type": "autobuy_waitlist", "opted_in": opted_in}


# ── Token streamer ────────────────────────────────────────────────────


async def _stream_text(text: str) -> AsyncGenerator[str, None]:
    """Yield words with a short delay for a natural streaming feel."""
    words = text.split(" ")
    for i, word in enumerate(words):
        token = word if i == 0 else f" {word}"
        yield token
        await asyncio.sleep(0.03)


# ── Error helpers ─────────────────────────────────────────────────────

_RECOVERABLE_FALLBACK = (
    "I'm having a little trouble thinking right now — "
    "please send your message again and I'll continue from where we left off."
)


def _is_pydantic_ai_retry_error(exc: Exception) -> bool:
    try:
        from pydantic_ai.exceptions import UnexpectedModelBehavior, UsageLimitExceeded
        return isinstance(exc, (UnexpectedModelBehavior, UsageLimitExceeded))
    except ImportError:
        pass
    msg = str(exc)
    return (
        "Exceeded maximum ret" in msg
        or "The next request would exceed" in msg
        or "request_limit" in msg
    )


# ── Buyer agent trigger ───────────────────────────────────────────────


async def _trigger_buyer_agent(
    buyer_id: str,
    criteria: Dict[str, Any],
) -> "BuyerHandoffResult":
    """
    Enable autonomous agent criteria on user and trigger an immediate buyer agent run.
    Returns a BuyerHandoffResult with the outcome.
    """
    from .schemas import BuyerHandoffResult

    try:
        from models.operations.users import user_enable_autonomous_agent

        # Build criteria for buyer agent
        agent_criteria = {
            "preferred_types": criteria.get("project_types", []),
            "preferred_co_benefits": [],
            "max_price_eur": criteria.get("max_price_eur") or 50.0,
            "min_vintage_year": 2020,
            "monthly_budget_eur": (criteria.get("target_tonnes") or 10) * (criteria.get("max_price_eur") or 20) * 2,
            "auto_approve_under_eur": min(
                5000.0,
                (criteria.get("target_tonnes") or 10) * (criteria.get("max_price_eur") or 20),
            ),
        }

        await user_enable_autonomous_agent(buyer_id, agent_criteria)
        logger.info("Enabled autonomous agent for buyer %s with criteria %s", buyer_id, agent_criteria)

    except Exception as exc:
        logger.error("Failed to enable autonomous agent for buyer %s: %s", buyer_id, exc)
        return BuyerHandoffResult(
            action="failed",
            error_message=f"Could not activate autonomous agent: {exc}",
        )

    try:
        from agents.buyer.agent import run_buyer_agent

        run_id = await run_buyer_agent(buyer_id, trigger="manual")
        if not run_id:
            return BuyerHandoffResult(
                action="skipped",
                run_id=None,
                rationale="Agent run could not be started (possibly already running).",
            )

        # Poll for result with a short timeout (wizard waits up to 30s)
        from models.operations.agent_runs import agent_run_get

        for _ in range(15):  # 15 × 2s = 30s max
            await asyncio.sleep(2)
            run = await agent_run_get(run_id)
            if run and run.data.status in ("completed", "failed", "awaiting_approval"):
                action = run.data.action_taken or "skipped"
                return BuyerHandoffResult(
                    action=cast(Any, action),
                    run_id=run_id,
                    listing_id=run.data.final_selection_id,
                    rationale=run.data.selection_rationale,
                )

        # Timed out — agent is still running
        return BuyerHandoffResult(
            action="proposed_for_approval",
            run_id=run_id,
            rationale="The agent is processing your purchase — check your dashboard for the result.",
        )

    except Exception as exc:
        logger.error("Buyer agent trigger failed for buyer %s: %s", buyer_id, exc, exc_info=True)
        return BuyerHandoffResult(
            action="failed",
            error_message=str(exc),
        )


# ── Autobuy waitlist activation ───────────────────────────────────────


async def _activate_autobuy_waitlist(
    buyer_id: str,
    criteria: Dict[str, Any],
) -> Optional[str]:
    """
    Enable autonomous agent on user profile and try an immediate run.
    Returns run_id if a run was started, None otherwise.
    """
    try:
        from models.operations.users import user_enable_autonomous_agent

        agent_criteria = {
            "preferred_types": criteria.get("project_types", []),
            "preferred_co_benefits": [],
            "max_price_eur": criteria.get("max_price_eur") or 50.0,
            "min_vintage_year": 2020,
            "monthly_budget_eur": (criteria.get("target_tonnes") or 10) * (criteria.get("max_price_eur") or 20) * 2,
            "auto_approve_under_eur": min(
                5000.0,
                (criteria.get("target_tonnes") or 10) * (criteria.get("max_price_eur") or 20),
            ),
        }

        await user_enable_autonomous_agent(buyer_id, agent_criteria)
        logger.info("Waitlist: enabled autonomous agent for buyer %s", buyer_id)

        # Try an immediate run in case there are now matching listings
        from agents.buyer.agent import run_buyer_agent
        run_id = await run_buyer_agent(buyer_id, trigger="manual")
        return run_id

    except Exception as exc:
        logger.warning("Could not activate autobuy for buyer %s: %s", buyer_id, exc)
        return None


# ── persist profile updates from wizard back to User doc ─────────────


async def _persist_profile_updates(buyer_id: str, final_state: WizardState) -> None:
    """
    Write wizard-extracted profile fields back to the User document so the
    buyer agent and future wizard sessions see consistent data.
    """
    try:
        from models.operations.users import user_update_buyer_profile, user_get_buyer_profile
        from models.entities.couchbase.users import BuyerProfile

        existing = await user_get_buyer_profile(buyer_id)
        bp = existing or BuyerProfile()

        changed = False
        fp = final_state.get("footprint_estimate")
        if fp and fp.get("midpoint") and not bp.annual_co2_tonnes_estimate:
            bp.annual_co2_tonnes_estimate = fp["midpoint"]
            changed = True

        prefs = final_state.get("extracted_preferences")
        if prefs:
            if prefs.project_types and not bp.preferred_project_types:
                bp.preferred_project_types = prefs.project_types
                changed = True
            if prefs.regions and not bp.preferred_regions:
                bp.preferred_regions = prefs.regions
                changed = True
            if prefs.max_price_eur and not bp.budget_per_tonne_max_eur:
                bp.budget_per_tonne_max_eur = prefs.max_price_eur
                changed = True

        wizard_bp = final_state.get("buyer_profile") or {}
        if wizard_bp.get("primary_offset_motivation") and not bp.primary_offset_motivation:
            bp.primary_offset_motivation = wizard_bp["primary_offset_motivation"]
            changed = True

        if changed:
            await user_update_buyer_profile(buyer_id, bp)
            logger.info("Persisted wizard profile updates for buyer %s", buyer_id)

    except Exception as exc:
        logger.warning("Could not persist profile updates for buyer %s: %s", buyer_id, exc)


# ── main entrypoint ───────────────────────────────────────────────────


async def run_wizard_turn(
    session_id: str,
    buyer_id: str,
    is_nudge: bool = False,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Run one wizard turn and yield SSE event dicts.

    Expects the user message to have already been persisted to the session
    by POST /wizard/session/{id}/message before this generator is consumed.
    When is_nudge=True (or detected automatically), the agent continues
    proactively without waiting for user input.
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

    # Determine if this is a nudge turn: no user message and history exists
    history = session.data.conversation_history or []
    has_history = len(history) > 0
    is_nudge = is_nudge or (not latest_user_msg and has_history)

    if not latest_user_msg:
        if is_nudge:
            # Agent continues proactively — injects a guidance prompt
            latest_user_msg = "__nudge__"
        else:
            # First ever turn — agent greets the buyer
            latest_user_msg = "Hello, I'd like to start offsetting my company's carbon emissions."

    # 3. Hydrate state
    initial_state: WizardState = state_from_session(session, latest_user_msg, is_nudge=is_nudge)

    # 4. Run the LangGraph graph (one node per turn)
    final_state: Optional[WizardState] = None
    response_text = ""
    graph_error = False

    # Steps that should auto-chain to the next node without waiting for user input.
    # e.g. listing_search → autobuy_waitlist runs both nodes in one turn.
    _AUTO_CHAIN_STEPS = {"autobuy_waitlist"}

    try:
        graph = get_wizard_graph()
        final_state = await graph.ainvoke(initial_state)

        # Auto-chain: if the node transitioned to an auto-chain step AND the user
        # has already opted in (detected in this same turn), run the next node
        # immediately so both messages arrive in one round-trip.
        # We do NOT auto-chain when there's no opt-in yet — that would cause the
        # autobuy_waitlist node to re-ask the same question redundantly.
        _next = final_state.get("next_step") if final_state is not None else None
        if (
            final_state is not None
            and _next in _AUTO_CHAIN_STEPS
            and _next != original_step
            and final_state.get("autobuy_opt_in", False)
        ):
            chained_step: str = cast(str, _next)
            chain_input: WizardState = {**final_state, "current_step": chained_step}  # type: ignore[misc]
            try:
                chained_state: WizardState = await graph.ainvoke(chain_input)
                first_response = (final_state.get("response_text") or "").strip()
                chained_response = (chained_state.get("response_text") or "").strip()
                merged: WizardState = {**final_state, **chained_state}  # type: ignore[misc]
                if first_response and chained_response:
                    merged["response_text"] = first_response + "\n\n" + chained_response
                elif chained_response:
                    merged["response_text"] = chained_response
                final_state = merged
                logger.info(
                    "Auto-chained %s → %s for session=%s",
                    original_step, chained_step, session_id,
                )
            except Exception as chain_exc:
                logger.warning(
                    "Auto-chain to %s failed for session=%s: %s",
                    chained_step, session_id, chain_exc,
                )

    except Exception as exc:
        if _is_pydantic_ai_retry_error(exc):
            logger.warning(
                "Wizard retry/limit error — session=%s step=%s error=%s: %s",
                session_id, original_step, type(exc).__name__, exc,
            )
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
        _valid_steps = {
            "profile_check", "onboarding", "footprint_estimate",
            "preference_elicitation", "listing_search",
            "recommendation", "order_creation", "autobuy_waitlist", "complete",
        }
        if new_step and new_step not in _valid_steps:
            new_step = None
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

            if final_state.get("autobuy_opt_in"):
                context_kwargs["autobuy_opt_in"] = True
                snapshot = final_state.get("autobuy_criteria_snapshot")
                if snapshot:
                    context_kwargs["autobuy_criteria_snapshot"] = snapshot

            if final_state.get("search_broadened"):
                context_kwargs["search_broadened"] = True

            # Terminal outcome flags
            if final_state.get("handoff_to_buyer_agent"):
                context_kwargs["handoff_to_buyer_agent"] = True
            if final_state.get("buyer_agent_run_id"):
                context_kwargs["buyer_agent_run_id"] = final_state.get("buyer_agent_run_id")
            if final_state.get("buyer_agent_outcome"):
                context_kwargs["buyer_agent_outcome"] = final_state.get("buyer_agent_outcome")
            if final_state.get("waitlist_opted_in"):
                context_kwargs["waitlist_opted_in"] = True
            if final_state.get("waitlist_declined"):
                context_kwargs["waitlist_declined"] = True
            if final_state.get("conversation_complete"):
                context_kwargs["conversation_complete"] = True

            if context_kwargs:
                await wizard_session_save_context(session_id, **context_kwargs)

            # Persist any wizard-extracted profile data back to User doc
            if not graph_error:
                await _persist_profile_updates(buyer_id, final_state)

    except Exception as exc:
        logger.warning(
            "Failed to persist wizard turn — session=%s step=%s: %s",
            session_id, original_step, exc,
        )

    # 10. Post-turn side effects: buyer agent handoff or waitlist activation
    if graph_error or final_state is None:
        return

    handoff = final_state.get("handoff_to_buyer_agent", False)
    waitlist_opted_in = final_state.get("waitlist_opted_in", False)

    if handoff:
        # Trigger buyer agent immediately and stream outcome
        criteria = final_state.get("autobuy_criteria_snapshot") or {}
        if not criteria:
            prefs = final_state.get("extracted_preferences")
            fp = final_state.get("footprint_estimate")
            bp = final_state.get("buyer_profile") or {}
            criteria = {
                "project_types": (prefs.project_types if prefs else []) or bp.get("preferred_project_types", []),
                "max_price_eur": (prefs.max_price_eur if prefs else None) or bp.get("budget_per_tonne_max_eur"),
                "target_tonnes": fp.get("midpoint") if fp else None,
            }

        handoff_result = await _trigger_buyer_agent(buyer_id, criteria)
        outcome_message = handoff_result.to_message()

        yield _buyer_handoff_event(handoff_result.action, outcome_message)
        yield _done_event(outcome_message)

        # Stream outcome message tokens too for smooth UX
        async for token in _stream_text(outcome_message):
            yield _token_event(token)

        try:
            await wizard_session_add_message(session_id, "assistant", outcome_message)
            await wizard_session_save_context(
                session_id,
                buyer_agent_run_id=handoff_result.run_id,
                buyer_agent_outcome=handoff_result.action,
                conversation_complete=True,
            )
        except Exception as exc:
            logger.warning("Could not persist buyer handoff outcome: %s", exc)

    elif waitlist_opted_in:
        snapshot = final_state.get("autobuy_criteria_snapshot") or {}
        run_id = await _activate_autobuy_waitlist(buyer_id, snapshot)
        yield _waitlist_event(opted_in=True)
        if run_id:
            try:
                await wizard_session_save_context(
                    session_id,
                    buyer_agent_run_id=run_id,
                )
            except Exception:
                pass
