from fastapi import APIRouter, Request, HTTPException, Query, Depends

from utils import log
from .users import router as users_router

logger = log.get_logger(__name__)

router = APIRouter(prefix="/api")
router.include_router(users_router)
