from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from models.operations.users import user_get_data_for_frontend
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
