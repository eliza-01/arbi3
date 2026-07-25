from app.exchanges.trading.errors import ExchangeRequestError
from app.local_settings.store import LocalSettingsStore


class UpdateTradingSettingsService:
    def __init__(self, settings_store: LocalSettingsStore) -> None:
        self._settings_store = settings_store

    def execute(
        self,
        *,
        position_usdt: float,
        leverage: int,
        rounding: str,
    ) -> dict:
        if position_usdt <= 0:
            raise ExchangeRequestError("Объём позиции должен быть больше 0 USDT")
        if leverage < 1 or leverage > 125:
            raise ExchangeRequestError("Плечо должно быть от 1x до 125x")
        normalized_rounding = "up" if rounding == "up" else "down"
        settings = self._settings_store.update(
            {
                "trading": {
                    "position_usdt": position_usdt,
                    "leverage": leverage,
                    "rounding": normalized_rounding,
                    "insurance_seconds": 0,
                },
            },
        )
        return settings.to_dict()["trading"]
