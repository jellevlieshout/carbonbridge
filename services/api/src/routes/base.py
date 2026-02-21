from fastapi import APIRouter, Request, HTTPException, Query, Depends

from utils import log
from .users import router as users_router
from .fake_registry import router as fake_registry_router

logger = log.get_logger(__name__)

router = APIRouter(prefix="/api")
router.include_router(users_router)
router.include_router(fake_registry_router)
