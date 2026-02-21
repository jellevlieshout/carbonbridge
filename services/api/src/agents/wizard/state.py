"""
LangGraph state for the buyer wizard agent.

Uses TypedDict (as recommended by LangGraph) for the graph state so field
merging from node return dicts works correctly. WizardState is the type
threaded through the graph; state_from_session hydrates it from Couchbase.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict

from models.entities.couchbase.wizard_sessions import (
    WizardSession,
    ConversationMessage,
    ExtractedPreferences,
)


class WizardState(TypedDict, total=False):
    """
    LangGraph state for one wizard turn.

    All fields are optional (total=False) so nodes can return partial dicts
    and LangGraph merges them into the existing state correctly.
    """

    # ── session identity ───────────────────────────────────────────────
    session_id: str
    buyer_id: str

    # ── step machine ──────────────────────────────────────────────────
    current_step: str   # one of the 7 WizardStep literals

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

    # ── output produced by the current node ──────────────────────────
    response_text: str
    next_step: Optional[str]  # step to transition to after this turn

    # ── error signal ──────────────────────────────────────────────────
    error: Optional[str]


def state_from_session(session: WizardSession, latest_message: str) -> WizardState:
    """Hydrate a WizardState dict from a persisted WizardSession document."""
    d = session.data
    return WizardState(
        session_id=session.id,
        buyer_id=d.buyer_id,
        current_step=d.current_step,
        conversation_history=list(d.conversation_history),
        latest_user_message=latest_message,
        extracted_preferences=d.extracted_preferences,
        # resume context from previous turns
        footprint_estimate=d.footprint_context,
        # Pass IDs so prompt can mention previously-shown listings
        recommended_listings=[{"id": lid} for lid in (d.recommended_listing_ids or [])],
        draft_order_id=d.draft_order_id,
        draft_order_total_eur=d.draft_order_total_eur,
        buyer_profile=None,
        response_text="",
        next_step=None,
        error=None,
    )
