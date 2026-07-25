from fastapi import APIRouter

from app.api.v1.endpoints.exchanges.binance.router import router as binance_router
from app.api.v1.endpoints.exchanges.bybit.router import router as bybit_router

router = APIRouter(prefix="/exchanges")
router.include_router(binance_router)
router.include_router(bybit_router)
