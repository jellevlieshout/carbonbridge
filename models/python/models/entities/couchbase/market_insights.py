from typing import Any, Dict, Optional
from datetime import datetime
from clients.couchbase import BaseModelCouchbase, BaseCouchbaseEntityData


class MarketInsightsData(BaseCouchbaseEntityData):
    credits_by_registry: Dict[str, Any] = {}
    credits_by_category: Dict[str, Any] = {}
    credits_by_country: Dict[str, Any] = {}
    coverage_by_category: Dict[str, Any] = {}
    computed_at: Optional[datetime] = None


class MarketInsights(BaseModelCouchbase[MarketInsightsData]):
    _collection_name = "market_insights"
