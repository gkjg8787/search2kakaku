from fastapi import APIRouter
from .urls import router as url_router
from .kakaku import router as kakaku_router

api_router = APIRouter(prefix="/api")
api_router.include_router(url_router)
api_router.include_router(kakaku_router)
