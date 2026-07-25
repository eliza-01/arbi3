from fastapi import Depends

from app.api.dependencies import get_container
from app.api.exchange_errors import exchange_http_error
from app.container import Container
from app.exchanges.trading.errors import ExchangeTradingError
from app.schemas.exchange_trading import BybitConnectRequest


async def connect_bybit(
    payload: BybitConnectRequest,
    container: Container = Depends(get_container),
) -> dict:
    try:
        return await container.connect_bybit.execute(payload.api_key, payload.secret_key)
    except ExchangeTradingError as exc:
        raise exchange_http_error(exc) from exc
