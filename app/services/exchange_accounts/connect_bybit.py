from app.exchanges.trading.errors import ExchangeRequestError
from app.local_settings.models import BybitConnectionSettings
from app.local_settings.store import LocalSettingsStore
from app.services.exchange_accounts.bybit_adapter_factory import BybitTradingAdapterFactory


class ConnectBybitService:
    def __init__(
        self,
        settings_store: LocalSettingsStore,
        adapter_factory: BybitTradingAdapterFactory,
    ) -> None:
        self._settings_store = settings_store
        self._adapter_factory = adapter_factory

    async def execute(self, api_key: str | None, secret_key: str | None) -> dict:
        current = self._settings_store.load().bybit
        candidate = BybitConnectionSettings(
            enabled=True,
            api_key=str(api_key if api_key is not None else current.api_key).strip(),
            secret_key=str(secret_key if secret_key is not None else current.secret_key).strip(),
        )
        async with self._adapter_factory.create(candidate) as adapter:
            status = await adapter.status()
        if status.state != "connected":
            raise ExchangeRequestError(status.message)
        settings = self._settings_store.update(
            {
                "bybit": {
                    "enabled": True,
                    "api_key": candidate.api_key,
                    "secret_key": candidate.secret_key,
                },
            },
        )
        return {
            **settings.to_dict(hide_secrets=True)["bybit"],
            "state": status.state,
            "message": status.message,
        }
