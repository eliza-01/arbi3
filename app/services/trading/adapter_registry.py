from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from app.exchanges.trading.errors import ExchangeRequestError
from app.services.exchange_accounts.binance_adapter_factory import BinanceTradingAdapterFactory
from app.services.exchange_accounts.bybit_adapter_factory import BybitTradingAdapterFactory


class TradingAdapterRegistry:
    def __init__(
        self,
        binance: BinanceTradingAdapterFactory,
        bybit: BybitTradingAdapterFactory,
    ) -> None:
        self._factories = {
            "binance": binance,
            "bybit": bybit,
        }

    @asynccontextmanager
    async def create(self, exchange_code: str) -> AsyncIterator[Any]:
        factory = self._factories.get(exchange_code.lower())
        if factory is None:
            raise ExchangeRequestError(
                f"Торговый адаптер {exchange_code.upper()} ещё не реализован"
            )
        async with factory.create() as adapter:
            yield adapter
