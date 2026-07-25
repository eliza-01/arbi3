from app.services.exchange_accounts.bybit_adapter_factory import BybitTradingAdapterFactory


class SetBybitLeverageService:
    def __init__(self, adapter_factory: BybitTradingAdapterFactory) -> None:
        self._adapter_factory = adapter_factory

    async def execute(self, symbol: str, leverage: int) -> dict:
        async with self._adapter_factory.create() as adapter:
            applied = await adapter.set_leverage(symbol, leverage)
        return {"exchange": "bybit", "symbol": symbol.upper(), "leverage": applied}
