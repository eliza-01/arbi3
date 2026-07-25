from datetime import UTC, datetime

from app.services.exchange_accounts.binance_adapter_factory import (
    BinanceTradingAdapterFactory,
)


class GetBinanceBalanceService:
    def __init__(self, adapter_factory: BinanceTradingAdapterFactory) -> None:
        self._adapter_factory = adapter_factory

    async def execute(self, currency: str = "USDT") -> dict:
        async with self._adapter_factory.create() as adapter:
            balance = await adapter.balance(currency)
        return {
            "exchange": "binance",
            "currency": balance.currency,
            "available": balance.available,
            "equity": balance.equity,
            "wallet_balance": balance.wallet_balance,
            "unrealized_pnl": balance.unrealized_pnl,
            "checked_at": datetime.now(UTC).isoformat(),
        }
