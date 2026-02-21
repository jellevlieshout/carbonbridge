from typing import Any, Dict, List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel
from clients.couchbase import BaseModelCouchbase, BaseCouchbaseEntityData

WizardStep = Literal[
    "profile_check", "onboarding", "footprint_estimate",
    "preference_elicitation", "listing_search",
    "recommendation", "order_creation"
]


class ConversationMessage(BaseModel):
    role: str
    content: str
    timestamp: Optional[datetime] = None


class ExtractedPreferences(BaseModel):
    project_types: List[str] = []
    regions: List[str] = []
    max_price_eur: Optional[float] = None
    co_benefits: List[str] = []


class WizardSessionData(BaseCouchbaseEntityData):
    buyer_id: str
    current_step: WizardStep = "profile_check"
    conversation_history: List[ConversationMessage] = []
    extracted_preferences: Optional[ExtractedPreferences] = None
    last_active_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    # ── graph context persisted for resume ────────────────────────────
    footprint_context: Optional[Dict[str, Any]] = None
    recommended_listing_ids: List[str] = []
    draft_order_id: Optional[str] = None
    draft_order_total_eur: Optional[float] = None
    # Whether listing search filters were already broadened once this session
    search_broadened: bool = False
    # ── autonomous-buy handoff ────────────────────────────────────────
    autobuy_opt_in: bool = False
    autobuy_criteria_snapshot: Optional[Dict[str, Any]] = None
    # ── terminal outcome signals ──────────────────────────────────────
    handoff_to_buyer_agent: bool = False
    buyer_agent_run_id: Optional[str] = None
    buyer_agent_outcome: Optional[str] = None
    waitlist_opted_in: bool = False
    waitlist_declined: bool = False
    conversation_complete: bool = False


class WizardSession(BaseModelCouchbase[WizardSessionData]):
    _collection_name = "wizard_sessions"
