from datetime import UTC, datetime

from app.services.exchange_accounts.bybit_adapter_factory import BybitTradingAdapterFactory


class GetBybitStatusService:
    def __init__(self, adapter_factory: BybitTradingAdapterFactory) -> None:
        self._adapter_factory = adapter_factory

    async def execute(self) -> dict:
        async with self._adapter_factory.create() as adapter:
            status = await adapter.status()
        return {
            "exchange": "bybit",
            "state": status.state,
            "message": status.message,
            "position_mode": status.position_mode,
            "checked_at": datetime.now(UTC).isoformat(),
        }
