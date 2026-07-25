from fastapi import APIRouter

from app.api.v1.endpoints.exchanges.binance.router import router as binance_router

router = APIRouter(prefix="/exchanges")
router.include_router(binance_router)
