from typing import List, Optional, Literal
from clients.couchbase import BaseModelCouchbase, BaseCouchbaseEntityData


class ListingData(BaseCouchbaseEntityData):
    seller_id: str
    registry_name: str
    registry_project_id: Optional[str] = None
    serial_number_range: Optional[str] = None
    project_name: str
    project_type: Literal[
        "afforestation", "renewable", "cookstoves", "methane_capture",
        "fuel_switching", "energy_efficiency", "agriculture", "other"
    ] = "other"
    project_country: Optional[str] = None
    vintage_year: Optional[int] = None
    quantity_tonnes: float = 0.0
    quantity_reserved: float = 0.0
    quantity_sold: float = 0.0
    price_per_tonne_eur: float
    verification_status: Literal["pending", "verified", "failed"] = "pending"
    methodology: Optional[str] = None
    co_benefits: List[str] = []
    description: Optional[str] = None
    supporting_documents: List[str] = []
    status: Literal["draft", "active", "paused", "sold_out"] = "draft"


class Listing(BaseModelCouchbase[ListingData]):
    _collection_name = "listings"
