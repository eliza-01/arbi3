from app.services.exchange_accounts.bybit_adapter_factory import BybitTradingAdapterFactory


class ListBybitPositionsService:
    def __init__(self, adapter_factory: BybitTradingAdapterFactory) -> None:
        self._adapter_factory = adapter_factory

    async def execute(self, symbol: str | None = None) -> list[dict]:
        async with self._adapter_factory.create() as adapter:
            positions = await adapter.positions(symbol)
        return [
            {
                "symbol": position.symbol,
                "direction": position.direction,
                "quantity": position.quantity,
                "entry_price": position.entry_price,
                "unrealized_pnl": position.unrealized_pnl,
                "position_index": position.position_index,
            }
            for position in positions
        ]
