from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from models.operations.users import user_get_data_for_frontend, user_update_onboarding
from utils import log
from .dependencies import current_user_get

logger = log.get_logger(__name__)

router = APIRouter(tags=["users"])

@router.get("/user_data", response_model=Dict[str, Any])
async def route_user_data_get(
    user: dict = Depends(current_user_get)
) -> Dict[str, Any]:
    """
    Retrieves resources for the authenticated user.
    """
    user_id = user.get("sub")

    if not user_id:
        logger.warning(f"User token does not contain sub (user_id). Claims: {user.keys()}")
        raise HTTPException(status_code=400, detail="User ID not found in token")

    try:
        return await user_get_data_for_frontend(user_id)
    except Exception as e:
        logger.error(f"Error retrieving user resources for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


class OnboardingRequest(BaseModel):
    role: str
    company_name: str
    sector: str | None = None
    country: str | None = None
    company_size_employees: int | None = None
    buyer_profile: dict | None = None


@router.put("/user_data/onboarding", response_model=Dict[str, Any])
async def route_user_onboarding(
    body: OnboardingRequest,
    user: dict = Depends(current_user_get),
) -> Dict[str, Any]:
    """
    Saves onboarding data (role, company info, buyer profile) for a new user.
    """
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID not found in token")

    if body.role not in ("buyer", "seller"):
        raise HTTPException(status_code=400, detail="Role must be 'buyer' or 'seller'")

    try:
        updated = await user_update_onboarding(user_id, body.model_dump(exclude_none=True))
        return {"user": updated.data.model_dump()}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error saving onboarding for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
