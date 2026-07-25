from fastapi import APIRouter

from app.api.v1.endpoints.trading.get_settings import get_trading_settings
from app.api.v1.endpoints.trading.update_settings import update_trading_settings

router = APIRouter(prefix="/trading", tags=["trading-settings"])
router.add_api_route("/settings", get_trading_settings, methods=["GET"])
router.add_api_route("/settings", update_trading_settings, methods=["PUT"])
