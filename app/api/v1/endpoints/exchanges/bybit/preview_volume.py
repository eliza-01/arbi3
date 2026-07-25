from typing import Literal

from fastapi import Depends, Query

from app.api.dependencies import get_container
from app.api.exchange_errors import exchange_http_error
from app.container import Container
from app.exchanges.trading.errors import ExchangeTradingError


async def preview_bybit_volume(
    symbol: str = Query(..., min_length=1),
    amount_usdt: float = Query(..., gt=0),
    rounding: Literal["down", "up"] = Query("down"),
    container: Container = Depends(get_container),
) -> dict:
    try:
        return await container.preview_bybit_volume.execute(symbol, amount_usdt, rounding)
    except ExchangeTradingError as exc:
        raise exchange_http_error(exc) from exc
