from fastapi import Depends, HTTPException, status

from app.api.dependencies import get_container
from app.api.exchange_errors import exchange_http_error
from app.container import Container
from app.exchanges.trading.errors import ExchangeTradingError
from app.schemas.exchange_trading import ArbitrageOpenRequest


async def open_arbitrage_pair(
    payload: ArbitrageOpenRequest,
    container: Container = Depends(get_container),
) -> dict:
    if not payload.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Для открытия двух позиций передайте confirm=true",
        )
    try:
        return await container.open_arbitrage_pair.execute(
            asset_id=payload.asset_id,
            exchange_a=payload.exchange_a,
            exchange_b=payload.exchange_b,
        )
    except ExchangeTradingError as exc:
        raise exchange_http_error(exc) from exc
