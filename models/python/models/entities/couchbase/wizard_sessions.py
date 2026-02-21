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
    # Raw footprint estimate returned by the estimate_footprint tool
    footprint_context: Optional[Dict[str, Any]] = None
    # Listings shown to the buyer in the recommendation step
    recommended_listing_ids: List[str] = []
    # Draft order if created
    draft_order_id: Optional[str] = None
    draft_order_total_eur: Optional[float] = None


class WizardSession(BaseModelCouchbase[WizardSessionData]):
    _collection_name = "wizard_sessions"
