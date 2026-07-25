from datetime import UTC, datetime

from app.services.exchange_accounts.binance_adapter_factory import (
    BinanceTradingAdapterFactory,
)


class GetBinanceStatusService:
    def __init__(self, adapter_factory: BinanceTradingAdapterFactory) -> None:
        self._adapter_factory = adapter_factory

    async def execute(self) -> dict:
        async with self._adapter_factory.create() as adapter:
            status = await adapter.status()
        return {
            "exchange": "binance",
            "state": status.state,
            "message": status.message,
            "position_mode": status.position_mode,
            "checked_at": datetime.now(UTC).isoformat(),
        }
