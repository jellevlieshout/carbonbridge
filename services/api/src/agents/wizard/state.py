"""
LangGraph state for the buyer wizard agent.

All fields are optional (total=False) so nodes can return partial dicts
and LangGraph merges them into the existing state correctly.

Terminal outcome signals:
  - handoff_to_buyer_agent: wizard handed off to buyer agent for immediate purchase
  - buyer_agent_run_id: run ID of the triggered buyer agent
  - buyer_agent_outcome: "purchased" | "proposed_for_approval" | "skipped" | "failed"
  - waitlist_opted_in: user accepted autonomous agent monitoring
  - conversation_complete: wizard flow is finished (any terminal outcome)
"""

from __future__ import annotations

from datetime import datetime
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

    # ── user / company profile (hydrated from User doc at session start) ──
    buyer_profile: Optional[Dict[str, Any]]
    company_name: Optional[str]
    company_sector: Optional[str]
    company_country: Optional[str]
    company_size_employees: Optional[int]

    # ── extracted preferences ─────────────────────────────────────────
    extracted_preferences: Optional[ExtractedPreferences]

    # ── context carried between steps ─────────────────────────────────
    footprint_estimate: Optional[Dict[str, Any]]
    recommended_listings: List[Dict[str, Any]]
    draft_order_id: Optional[str]
    draft_order_total_eur: Optional[float]

    # ── listing search state ──────────────────────────────────────────
    search_broadened: bool   # True once we have already loosened filters

    # ── autonomous-buy handoff ────────────────────────────────────────
    autobuy_opt_in: bool
    autobuy_criteria_snapshot: Optional[Dict[str, Any]]

    # ── terminal outcome signals ──────────────────────────────────────
    handoff_to_buyer_agent: bool     # wizard triggered buyer agent immediately
    buyer_agent_run_id: Optional[str]  # run ID of triggered agent run
    buyer_agent_outcome: Optional[str]  # purchased | proposed_for_approval | skipped | failed
    buyer_agent_message: Optional[str]  # human-readable outcome message
    waitlist_opted_in: bool          # user accepted future autonomous buy
    waitlist_declined: bool          # user explicitly declined
    conversation_complete: bool      # any terminal path was reached

    # ── output produced by the current node ──────────────────────────
    response_text: str
    next_step: Optional[str]
    suggested_responses: List[str]   # LLM-generated quick-reply suggestions

    # ── error signal ──────────────────────────────────────────────────
    error: Optional[str]

    # ── proactive / time awareness ────────────────────────────────────
    is_nudge: bool                          # True when agent continues proactively
    session_created_at: Optional[datetime]  # When this session started
    session_last_active_at: Optional[datetime]  # Last activity timestamp


def state_from_session(
    session: WizardSession,
    latest_message: str,
    is_nudge: bool = False,
) -> WizardState:
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
        company_name=None,
        company_sector=None,
        company_country=None,
        company_size_employees=None,
        search_broadened=getattr(d, "search_broadened", False),
        autobuy_opt_in=getattr(d, "autobuy_opt_in", False),
        autobuy_criteria_snapshot=getattr(d, "autobuy_criteria_snapshot", None),
        handoff_to_buyer_agent=False,
        buyer_agent_run_id=None,
        buyer_agent_outcome=None,
        buyer_agent_message=None,
        waitlist_opted_in=False,
        waitlist_declined=False,
        conversation_complete=False,
        response_text="",
        next_step=None,
        suggested_responses=[],
        error=None,
        is_nudge=is_nudge,
        session_created_at=getattr(d, "created_at", None),
        session_last_active_at=getattr(d, "last_active_at", None),
    )
