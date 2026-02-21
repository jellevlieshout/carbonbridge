from typing import Any, Dict, List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel
from clients.couchbase import BaseModelCouchbase, BaseCouchbaseEntityData


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
    current_step: Literal[
        "profile_check", "onboarding", "footprint_estimate",
        "preference_elicitation", "listing_search",
        "recommendation", "order_creation"
    ] = "profile_check"
    conversation_history: List[ConversationMessage] = []
    extracted_preferences: Optional[ExtractedPreferences] = None
    last_active_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class WizardSession(BaseModelCouchbase[WizardSessionData]):
    _collection_name = "wizard_sessions"
