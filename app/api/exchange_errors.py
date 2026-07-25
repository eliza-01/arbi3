from fastapi import HTTPException, status

from app.exchanges.trading.errors import ExchangeTradingError


def exchange_http_error(error: ExchangeTradingError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(error),
    )
