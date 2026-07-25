from app.services.exchange_accounts.binance_adapter_factory import (
    BinanceTradingAdapterFactory,
)


class SetBinanceLeverageService:
    def __init__(self, adapter_factory: BinanceTradingAdapterFactory) -> None:
        self._adapter_factory = adapter_factory

    async def execute(self, symbol: str, leverage: int) -> dict:
        async with self._adapter_factory.create() as adapter:
            applied = await adapter.set_leverage(symbol, leverage)
        return {"exchange": "binance", "symbol": symbol.upper(), "leverage": applied}
