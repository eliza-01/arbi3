from datetime import UTC, datetime

from app.services.exchange_accounts.bybit_adapter_factory import BybitTradingAdapterFactory


class GetBybitBalanceService:
    def __init__(self, adapter_factory: BybitTradingAdapterFactory) -> None:
        self._adapter_factory = adapter_factory

    async def execute(self, currency: str = "USDT") -> dict:
        async with self._adapter_factory.create() as adapter:
            balance = await adapter.balance(currency)
        return {
            "exchange": "bybit",
            "currency": balance.currency,
            "available": balance.available,
            "equity": balance.equity,
            "wallet_balance": balance.wallet_balance,
            "unrealized_pnl": balance.unrealized_pnl,
            "checked_at": datetime.now(UTC).isoformat(),
        }
