from app.services.exchange_accounts.binance_adapter_factory import (
    BinanceTradingAdapterFactory,
)


class PreviewBinanceVolumeService:
    def __init__(self, adapter_factory: BinanceTradingAdapterFactory) -> None:
        self._adapter_factory = adapter_factory

    async def execute(self, symbol: str, amount_usdt: float, rounding: str) -> dict:
        async with self._adapter_factory.create() as adapter:
            previews = await adapter.preview_volume(symbol, amount_usdt, rounding)
        return {
            "exchange": "binance",
            "symbol": previews["buy"].symbol,
            "amount_usdt": amount_usdt,
            "rounding": "up" if rounding == "up" else "down",
            "buy": _serialize(previews["buy"]),
            "sell": _serialize(previews["sell"]),
        }


def _serialize(value) -> dict:
    return {
        "side": value.side,
        "price": value.price,
        "quantity": value.quantity,
        "rounded_amount_usdt": value.rounded_amount_usdt,
        "min_quantity": value.min_quantity,
        "max_quantity": value.max_quantity,
        "quantity_step": value.quantity_step,
        "min_notional_usdt": value.min_notional_usdt,
    }
