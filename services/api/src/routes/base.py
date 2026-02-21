from fastapi import APIRouter
from utils import log

from .internal import router as internal_router
from .listings import router as listings_router
from .users import router as users_router
from .wizard import router as wizard_router
from .sellers import router as sellers_router
from .orders import router as orders_router
from .webhooks import router as webhooks_router
from .agent import router as agent_router

logger = log.get_logger(__name__)

router = APIRouter(prefix="/api")
router.include_router(users_router)
router.include_router(listings_router)
router.include_router(internal_router)
router.include_router(wizard_router)
router.include_router(sellers_router)
router.include_router(orders_router)
router.include_router(webhooks_router)
router.include_router(agent_router)


@router.post("/seed", tags=["dev"])
async def route_seed():
    """Populate the database with fake seed data (dev only)."""
    from seed import run_seed

    counts = await run_seed()
    return {"status": "ok", "seeded": counts}
