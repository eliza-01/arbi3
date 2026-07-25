from fastapi import APIRouter

from app.api.v1.endpoints.assets.router import router as assets_router
from app.api.v1.endpoints.blacklist.router import router as blacklist_router
from app.api.v1.endpoints.favorites.router import router as favorites_router
from app.api.v1.endpoints.exchanges.router import router as exchanges_router
from app.api.v1.endpoints.trading.router import router as trading_router
from app.api.v1.endpoints.runtime.router import router as runtime_router
from app.api.v1.endpoints.system.router import router as system_router

router = APIRouter(prefix="/api/v1")
router.include_router(assets_router)
router.include_router(blacklist_router)
router.include_router(favorites_router)
router.include_router(exchanges_router)
router.include_router(trading_router)
router.include_router(runtime_router)
router.include_router(system_router)
