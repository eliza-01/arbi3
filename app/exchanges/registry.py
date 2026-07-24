from app.exchanges.binance.adapter import BinanceAdapter
from app.exchanges.bybit.adapter import BybitAdapter
from app.exchanges.contracts import ExchangeAdapter


class ExchangeRegistry:
    def __init__(self) -> None:
        adapters: list[ExchangeAdapter] = [BinanceAdapter(), BybitAdapter()]
        self._adapters = {adapter.code: adapter for adapter in adapters}

    def all(self) -> list[ExchangeAdapter]:
        return list(self._adapters.values())

    def get(self, code: str) -> ExchangeAdapter:
        return self._adapters[code]

    async def close(self) -> None:
        for adapter in self._adapters.values():
            close = getattr(adapter, "close", None)
            if close is not None:
                await close()
