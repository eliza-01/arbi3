from app.exchanges.trading.models import ClosePositionRequest
from app.local_settings.store import LocalSettingsStore
from app.services.exchange_accounts.bybit_adapter_factory import BybitTradingAdapterFactory


class CloseBybitPositionService:
    def __init__(
        self,
        settings_store: LocalSettingsStore,
        adapter_factory: BybitTradingAdapterFactory,
    ) -> None:
        self._settings_store = settings_store
        self._adapter_factory = adapter_factory

    async def execute(
        self,
        *,
        symbol: str,
        direction: str,
        amount_usdt: float | None,
        rounding: str | None,
    ) -> dict:
        defaults = self._settings_store.load().trading
        request = ClosePositionRequest(
            symbol=symbol,
            direction="short" if direction == "short" else "long",
            amount_usdt=amount_usdt,
            rounding="up" if (rounding or defaults.rounding) == "up" else "down",
        )
        async with self._adapter_factory.create() as adapter:
            result = await adapter.close_position(request)
        return {
            "success": result.success,
            "message": result.message,
            "order_id": result.order_id,
            "raw": result.raw,
        }
