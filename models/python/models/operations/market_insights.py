from typing import Optional
from models.entities.couchbase.market_insights import MarketInsights, MarketInsightsData

MARKET_INSIGHTS_KEY = "market_insights_latest"


async def market_insights_get() -> Optional[MarketInsights]:
    return await MarketInsights.get(MARKET_INSIGHTS_KEY)


async def market_insights_upsert(data: MarketInsightsData) -> MarketInsights:
    return await MarketInsights.create_or_update(key=MARKET_INSIGHTS_KEY, data=data)
