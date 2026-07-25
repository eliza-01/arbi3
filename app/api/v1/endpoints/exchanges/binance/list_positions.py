from fastapi import Depends, Query

from app.api.dependencies import get_container
from app.api.exchange_errors import exchange_http_error
from app.container import Container
from app.exchanges.trading.errors import ExchangeTradingError


async def list_binance_positions(
    symbol: str | None = Query(default=None),
    container: Container = Depends(get_container),
) -> dict:
    try:
        items = await container.list_binance_positions.execute(symbol)
        return {"items": items}
    except ExchangeTradingError as exc:
        raise exchange_http_error(exc) from exc
