from fastapi import APIRouter

from app.api.v1.endpoints.exchanges.bybit.close_position import close_bybit_position
from app.api.v1.endpoints.exchanges.bybit.connect import connect_bybit
from app.api.v1.endpoints.exchanges.bybit.disconnect import disconnect_bybit
from app.api.v1.endpoints.exchanges.bybit.get_balance import get_bybit_balance
from app.api.v1.endpoints.exchanges.bybit.get_settings import get_bybit_settings
from app.api.v1.endpoints.exchanges.bybit.get_status import get_bybit_status
from app.api.v1.endpoints.exchanges.bybit.list_positions import list_bybit_positions
from app.api.v1.endpoints.exchanges.bybit.open_position import open_bybit_position
from app.api.v1.endpoints.exchanges.bybit.preview_volume import preview_bybit_volume
from app.api.v1.endpoints.exchanges.bybit.set_leverage import set_bybit_leverage

router = APIRouter(prefix="/bybit", tags=["bybit-trading"])
router.add_api_route("/settings", get_bybit_settings, methods=["GET"])
router.add_api_route("/status", get_bybit_status, methods=["GET"])
router.add_api_route("/balance", get_bybit_balance, methods=["GET"])
router.add_api_route("/connect", connect_bybit, methods=["POST"])
router.add_api_route("/disconnect", disconnect_bybit, methods=["POST"])
router.add_api_route("/volume-preview", preview_bybit_volume, methods=["GET"])
router.add_api_route("/positions", list_bybit_positions, methods=["GET"])
router.add_api_route("/leverage", set_bybit_leverage, methods=["PUT"])
router.add_api_route("/positions/open", open_bybit_position, methods=["POST"])
router.add_api_route("/positions/close", close_bybit_position, methods=["POST"])
