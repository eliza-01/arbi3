from fastapi import Depends

from app.api.dependencies import get_container
from app.api.exchange_errors import exchange_http_error
from app.container import Container
from app.exchanges.trading.errors import ExchangeTradingError
from app.schemas.exchange_trading import BybitLeverageRequest


async def set_bybit_leverage(
    payload: BybitLeverageRequest,
    container: Container = Depends(get_container),
) -> dict:
    try:
        return await container.set_bybit_leverage.execute(payload.symbol, payload.leverage)
    except ExchangeTradingError as exc:
        raise exchange_http_error(exc) from exc
