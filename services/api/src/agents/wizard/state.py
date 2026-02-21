"""
LangGraph state for the buyer wizard agent.

All fields are optional (total=False) so nodes can return partial dicts
and LangGraph merges them into the existing state correctly.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict

from models.entities.couchbase.wizard_sessions import (
    ConversationMessage,
    ExtractedPreferences,
    WizardSession,
)


class WizardState(TypedDict, total=False):
    # ── session identity ───────────────────────────────────────────────
    session_id: str
    buyer_id: str

    # ── step machine ──────────────────────────────────────────────────
    current_step: str

    # ── conversation ──────────────────────────────────────────────────
    conversation_history: List[ConversationMessage]
    latest_user_message: str

    # ── extracted data ────────────────────────────────────────────────
    extracted_preferences: Optional[ExtractedPreferences]

    # ── context carried between steps ─────────────────────────────────
    footprint_estimate: Optional[Dict[str, Any]]
    recommended_listings: List[Dict[str, Any]]
    draft_order_id: Optional[str]
    draft_order_total_eur: Optional[float]
    buyer_profile: Optional[Dict[str, Any]]

    # ── listing search state ──────────────────────────────────────────
    search_broadened: bool   # True once we have already loosened filters

    # ── autonomous-buy handoff ────────────────────────────────────────
    autobuy_opt_in: bool
    autobuy_criteria_snapshot: Optional[Dict[str, Any]]

    # ── output produced by the current node ──────────────────────────
    response_text: str
    next_step: Optional[str]

    # ── error signal ──────────────────────────────────────────────────
    error: Optional[str]


def state_from_session(session: WizardSession, latest_message: str) -> WizardState:
    """Hydrate a WizardState from a persisted WizardSession document."""
    d = session.data
    return WizardState(
        session_id=session.id,
        buyer_id=d.buyer_id,
        current_step=d.current_step,
        conversation_history=list(d.conversation_history),
        latest_user_message=latest_message,
        extracted_preferences=d.extracted_preferences,
        footprint_estimate=d.footprint_context,
        recommended_listings=[{"id": lid} for lid in (d.recommended_listing_ids or [])],
        draft_order_id=d.draft_order_id,
        draft_order_total_eur=d.draft_order_total_eur,
        buyer_profile=None,
        search_broadened=getattr(d, "search_broadened", False),
        autobuy_opt_in=getattr(d, "autobuy_opt_in", False),
        autobuy_criteria_snapshot=getattr(d, "autobuy_criteria_snapshot", None),
        response_text="",
        next_step=None,
        error=None,
    )
