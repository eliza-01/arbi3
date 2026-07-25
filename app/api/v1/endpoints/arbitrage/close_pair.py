from fastapi import Depends, HTTPException, status

from app.api.dependencies import get_container
from app.api.exchange_errors import exchange_http_error
from app.container import Container
from app.exchanges.trading.errors import ExchangeTradingError
from app.schemas.exchange_trading import ArbitrageCloseRequest


async def close_arbitrage_pair(
    trade_id: int,
    payload: ArbitrageCloseRequest,
    container: Container = Depends(get_container),
) -> dict:
    if not payload.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Для закрытия двух позиций передайте confirm=true",
        )
    try:
        return await container.close_arbitrage_pair.execute(trade_id)
    except ExchangeTradingError as exc:
        raise exchange_http_error(exc) from exc
