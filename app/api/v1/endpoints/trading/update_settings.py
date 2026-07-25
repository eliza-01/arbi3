from fastapi import Depends

from app.api.dependencies import get_container
from app.api.exchange_errors import exchange_http_error
from app.container import Container
from app.exchanges.trading.errors import ExchangeTradingError
from app.schemas.exchange_trading import TradingSettingsUpdateRequest


async def update_trading_settings(
    payload: TradingSettingsUpdateRequest,
    container: Container = Depends(get_container),
) -> dict:
    try:
        return container.update_trading_settings.execute(
            position_usdt=payload.position_usdt,
            leverage=payload.leverage,
            rounding=payload.rounding,
            insurance_seconds=payload.insurance_seconds,
        )
    except ExchangeTradingError as exc:
        raise exchange_http_error(exc) from exc
