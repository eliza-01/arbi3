from fastapi import APIRouter

from app.api.v1.endpoints.arbitrage.close_pair import close_arbitrage_pair
from app.api.v1.endpoints.arbitrage.list_active import list_active_arbitrage_trades
from app.api.v1.endpoints.arbitrage.open_pair import open_arbitrage_pair

router = APIRouter(prefix="/arbitrage/trades", tags=["arbitrage"])
router.add_api_route("", list_active_arbitrage_trades, methods=["GET"])
router.add_api_route("/open", open_arbitrage_pair, methods=["POST"])
router.add_api_route("/{trade_id}/close", close_arbitrage_pair, methods=["POST"])
