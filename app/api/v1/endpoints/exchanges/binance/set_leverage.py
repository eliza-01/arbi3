from fastapi import Depends

from app.api.dependencies import get_container
from app.api.exchange_errors import exchange_http_error
from app.container import Container
from app.exchanges.trading.errors import ExchangeTradingError
from app.schemas.exchange_trading import BinanceLeverageRequest


async def set_binance_leverage(
    payload: BinanceLeverageRequest,
    container: Container = Depends(get_container),
) -> dict:
    try:
        return await container.set_binance_leverage.execute(
            payload.symbol,
            payload.leverage,
        )
    except ExchangeTradingError as exc:
        raise exchange_http_error(exc) from exc
