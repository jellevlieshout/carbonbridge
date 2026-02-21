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


@router.get("/ledger", tags=["dev"])
async def route_ledger_status():
    """Inspect TigerBeetle ledger state: platform account + all user accounts with TB accounts."""
    from clients.tigerbeetle.client import (
        get_tigerbeetle_client,
        lookup_account_balance,
        PLATFORM_ESCROW_ACCOUNT_ID,
    )
    from models.entities.couchbase.users import User

    try:
        get_tigerbeetle_client()
    except Exception as e:
        return {"status": "error", "detail": f"Cannot connect to TigerBeetle: {e}"}

    # Platform escrow account
    platform = lookup_account_balance(PLATFORM_ESCROW_ACCOUNT_ID)

    # Query users that have TigerBeetle accounts
    keyspace = User.get_keyspace()
    rows = await keyspace.query(
        f"SELECT META().id, * FROM {keyspace} "
        f"WHERE tigerbeetle_settled_account_id IS NOT NULL"
    )

    user_accounts = []
    for row in rows:
        data = row.get("users")
        if not data:
            continue
        u = User(id=row["id"], data=data)
        settled_balance = lookup_account_balance(u.data.tigerbeetle_settled_account_id)
        user_accounts.append({
            "user_id": u.id,
            "email": u.data.email,
            "role": u.data.role,
            "settled_account_id": u.data.tigerbeetle_settled_account_id,
            "balance_cents": settled_balance,
        })

    return {
        "status": "ok",
        "platform_escrow": {
            "account_id": PLATFORM_ESCROW_ACCOUNT_ID,
            "balance_cents": platform,
        },
        "user_accounts": user_accounts,
    }
