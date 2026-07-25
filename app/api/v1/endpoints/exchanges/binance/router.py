from fastapi import APIRouter

from app.api.v1.endpoints.exchanges.binance.close_position import (
    close_binance_position,
)
from app.api.v1.endpoints.exchanges.binance.connect import connect_binance
from app.api.v1.endpoints.exchanges.binance.disconnect import disconnect_binance
from app.api.v1.endpoints.exchanges.binance.get_balance import get_binance_balance
from app.api.v1.endpoints.exchanges.binance.get_settings import get_binance_settings
from app.api.v1.endpoints.exchanges.binance.get_status import get_binance_status
from app.api.v1.endpoints.exchanges.binance.list_positions import (
    list_binance_positions,
)
from app.api.v1.endpoints.exchanges.binance.open_position import open_binance_position
from app.api.v1.endpoints.exchanges.binance.preview_volume import (
    preview_binance_volume,
)
from app.api.v1.endpoints.exchanges.binance.set_leverage import set_binance_leverage

router = APIRouter(prefix="/binance", tags=["binance-trading"])
router.add_api_route("/settings", get_binance_settings, methods=["GET"])
router.add_api_route("/status", get_binance_status, methods=["GET"])
router.add_api_route("/balance", get_binance_balance, methods=["GET"])
router.add_api_route("/connect", connect_binance, methods=["POST"])
router.add_api_route("/disconnect", disconnect_binance, methods=["POST"])
router.add_api_route("/volume-preview", preview_binance_volume, methods=["GET"])
router.add_api_route("/positions", list_binance_positions, methods=["GET"])
router.add_api_route("/leverage", set_binance_leverage, methods=["PUT"])
router.add_api_route("/positions/open", open_binance_position, methods=["POST"])
router.add_api_route("/positions/close", close_binance_position, methods=["POST"])
