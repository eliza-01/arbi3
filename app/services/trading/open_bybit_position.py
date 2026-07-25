from app.exchanges.trading.models import OpenPositionRequest
from app.local_settings.store import LocalSettingsStore
from app.services.exchange_accounts.bybit_adapter_factory import BybitTradingAdapterFactory


class OpenBybitPositionService:
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
        leverage: int | None,
        rounding: str | None,
    ) -> dict:
        defaults = self._settings_store.load().trading
        request = OpenPositionRequest(
            symbol=symbol,
            direction="short" if direction == "short" else "long",
            amount_usdt=amount_usdt if amount_usdt is not None else defaults.position_usdt,
            leverage=leverage if leverage is not None else defaults.leverage,
            rounding="up" if (rounding or defaults.rounding) == "up" else "down",
        )
        async with self._adapter_factory.create() as adapter:
            result = await adapter.open_position(request)
        return {
            "success": result.success,
            "message": result.message,
            "order_id": result.order_id,
            "raw": result.raw,
        }
