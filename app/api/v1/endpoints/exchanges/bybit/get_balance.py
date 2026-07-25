from fastapi import Depends, Query

from app.api.dependencies import get_container
from app.api.exchange_errors import exchange_http_error
from app.container import Container
from app.exchanges.trading.errors import ExchangeTradingError


async def get_bybit_balance(
    currency: str = Query("USDT", min_length=1, max_length=16),
    container: Container = Depends(get_container),
) -> dict:
    try:
        return await container.get_bybit_balance.execute(currency)
    except ExchangeTradingError as exc:
        raise exchange_http_error(exc) from exc
