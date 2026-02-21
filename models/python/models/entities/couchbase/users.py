from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from clients.couchbase import BaseModelCouchbase, BaseCouchbaseEntityData


class BuyerProfile(BaseModel):
    annual_co2_tonnes_estimate: Optional[float] = None
    primary_offset_motivation: Optional[Literal["compliance", "esg_reporting", "brand", "personal"]] = None
    preferred_project_types: List[str] = []
    preferred_regions: List[str] = []
    budget_per_tonne_max_eur: Optional[float] = None
    autonomous_agent_enabled: bool = False
    autonomous_agent_criteria: Optional[dict] = None
    autonomous_agent_wallet_id: Optional[str] = None


class UserData(BaseCouchbaseEntityData):
    email: str
    hashed_password: Optional[str] = Field(default=None, exclude=True)
    role: Literal["buyer", "seller", "admin"] = "buyer"
    company_name: Optional[str] = None
    company_size_employees: Optional[int] = None
    sector: Optional[str] = None
    country: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    stripe_connect_account_id: Optional[str] = None
    stripe_connect_onboarding_complete: bool = False
    tigerbeetle_pending_account_id: Optional[str] = None
    tigerbeetle_settled_account_id: Optional[str] = None
    buyer_profile: Optional[BuyerProfile] = None


class User(BaseModelCouchbase[UserData]):
    _collection_name = "users"
