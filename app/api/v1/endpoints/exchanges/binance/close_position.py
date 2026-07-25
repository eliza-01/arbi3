from fastapi import Depends, HTTPException, status

from app.api.dependencies import get_container
from app.api.exchange_errors import exchange_http_error
from app.container import Container
from app.exchanges.trading.errors import ExchangeTradingError
from app.schemas.exchange_trading import BinanceClosePositionRequest


async def close_binance_position(
    payload: BinanceClosePositionRequest,
    container: Container = Depends(get_container),
) -> dict:
    if not payload.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Для исполнения market-ордера передайте confirm=true",
        )
    try:
        return await container.close_binance_position.execute(
            symbol=payload.symbol,
            direction=payload.direction,
            amount_usdt=payload.amount_usdt,
            quantity=payload.quantity,
            rounding=payload.rounding,
        )
    except ExchangeTradingError as exc:
        raise exchange_http_error(exc) from exc
