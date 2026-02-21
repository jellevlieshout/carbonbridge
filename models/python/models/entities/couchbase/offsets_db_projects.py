from typing import Optional, Literal
from datetime import datetime
from clients.couchbase import BaseModelCouchbase, BaseCouchbaseEntityData


class OffsetsDBProjectData(BaseCouchbaseEntityData):
    offsets_db_project_id: str
    registry: Literal["ACR", "ART", "CAR", "GLD", "VCS"]
    name: Optional[str] = None
    category: Optional[Literal[
        "Forest", "Renewable Energy", "GHG Management",
        "Energy Efficiency", "Fuel Switching", "Agriculture", "Other"
    ]] = None
    project_type: Optional[str] = None
    country: Optional[str] = None
    protocol: Optional[str] = None
    methodology: Optional[str] = None
    total_credits_issued: float = 0.0
    total_credits_retired: float = 0.0
    first_issuance_date: Optional[datetime] = None
    last_issuance_date: Optional[datetime] = None
    market_type: Optional[Literal["compliance", "voluntary"]] = None
    status: Optional[str] = None
    offsets_db_url: Optional[str] = None
    raw_data: Optional[dict] = None
    synced_at: Optional[datetime] = None


class OffsetsDBProject(BaseModelCouchbase[OffsetsDBProjectData]):
    _collection_name = "offsets_db_projects"
