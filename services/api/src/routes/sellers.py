import stripe

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from models.entities.couchbase.users import User
from utils import env, log
from .dependencies import require_authenticated

logger = log.get_logger(__name__)

router = APIRouter(prefix="/sellers", tags=["sellers"])

STRIPE_SECRET_KEY = env.EnvVarSpec(
    id="STRIPE_SECRET_KEY", is_optional=True, is_secret=True
)


def _get_stripe():
    key = env.parse(STRIPE_SECRET_KEY)
    if not key:
        raise HTTPException(status_code=503, detail="Stripe is not configured")
    stripe.api_key = key
    return stripe


# ---------------------------------------------------------------------------
# POST /sellers/onboarding — create Stripe Connect account + return link
# ---------------------------------------------------------------------------

class OnboardingResponse(BaseModel):
    account_id: str
    onboarding_url: str


@router.post("/onboarding", response_model=OnboardingResponse)
async def route_seller_onboarding(
    request: Request,
    user: dict = Depends(require_authenticated),
):
    user_id = user["sub"]
    db_user = user.get("db_user")
    if not db_user:
        raise HTTPException(status_code=500, detail="User not loaded")

    s = _get_stripe()

    # Reuse existing Connect account if one exists
    account_id = db_user.data.stripe_connect_account_id
    if not account_id:
        account = s.Account.create(
            type="express",
            country=db_user.data.country or "IE",
            email=db_user.data.email,
            capabilities={
                "transfers": {"requested": True},
            },
            metadata={"carbonbridge_user_id": user_id},
        )
        account_id = account.id

        # Persist to user document
        db_user.data.stripe_connect_account_id = account_id
        await User.update(db_user)

    # Build return URL from request origin
    origin = str(request.base_url).rstrip("/")
    account_link = s.AccountLink.create(
        account=account_id,
        refresh_url=f"{origin}/seller/onboarding?refresh=true",
        return_url=f"{origin}/seller/listings",
        type="account_onboarding",
    )

    return OnboardingResponse(
        account_id=account_id,
        onboarding_url=account_link.url,
    )


# ---------------------------------------------------------------------------
# GET /sellers/onboarding/status — check if onboarding is complete
# ---------------------------------------------------------------------------

class OnboardingStatusResponse(BaseModel):
    has_account: bool
    onboarding_complete: bool
    payouts_enabled: bool
    charges_enabled: bool


@router.get("/onboarding/status", response_model=OnboardingStatusResponse)
async def route_seller_onboarding_status(
    user: dict = Depends(require_authenticated),
):
    db_user = user.get("db_user")
    if not db_user:
        raise HTTPException(status_code=500, detail="User not loaded")

    account_id = db_user.data.stripe_connect_account_id
    if not account_id:
        return OnboardingStatusResponse(
            has_account=False,
            onboarding_complete=False,
            payouts_enabled=False,
            charges_enabled=False,
        )

    s = _get_stripe()
    account = s.Account.retrieve(account_id)

    is_complete = bool(account.details_submitted)

    # Update cached flag if status changed
    if is_complete and not db_user.data.stripe_connect_onboarding_complete:
        db_user.data.stripe_connect_onboarding_complete = True
        await User.update(db_user)

    return OnboardingStatusResponse(
        has_account=True,
        onboarding_complete=is_complete,
        payouts_enabled=bool(account.payouts_enabled),
        charges_enabled=bool(account.charges_enabled),
    )
