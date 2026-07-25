from app.exchanges.trading.errors import ExchangeRequestError
from app.local_settings.models import BinanceConnectionSettings
from app.local_settings.store import LocalSettingsStore
from app.services.exchange_accounts.binance_adapter_factory import (
    BinanceTradingAdapterFactory,
)


class ConnectBinanceService:
    def __init__(
        self,
        settings_store: LocalSettingsStore,
        adapter_factory: BinanceTradingAdapterFactory,
    ) -> None:
        self._settings_store = settings_store
        self._adapter_factory = adapter_factory

    async def execute(self, api_key: str | None, secret_key: str | None) -> dict:
        current = self._settings_store.load().binance
        candidate = BinanceConnectionSettings(
            enabled=True,
            api_key=(api_key if api_key is not None else current.api_key).strip(),
            secret_key=(
                secret_key if secret_key is not None else current.secret_key
            ).strip(),
        )
        if not candidate.api_key or not candidate.secret_key:
            raise ExchangeRequestError("Укажите Binance API key и Secret key")

        async with self._adapter_factory.create(candidate) as adapter:
            status = await adapter.status()
        if status.state != "connected":
            raise ExchangeRequestError(status.message)

        settings = self._settings_store.update(
            {
                "binance": {
                    "enabled": True,
                    "api_key": candidate.api_key,
                    "secret_key": candidate.secret_key,
                },
            },
        )
        return {
            **settings.to_dict(hide_secrets=True)["binance"],
            "state": status.state,
            "message": status.message,
            "position_mode": status.position_mode,
        }
