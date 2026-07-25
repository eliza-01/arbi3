from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from app.exchanges.bybit.trading_adapter import BybitTradingAdapter
from app.exchanges.trading.models import ExchangeCredentials, ExchangeTradingConfig
from app.local_settings.models import BybitConnectionSettings
from app.local_settings.store import LocalSettingsStore


class BybitTradingAdapterFactory:
    def __init__(self, settings_store: LocalSettingsStore) -> None:
        self._settings_store = settings_store

    @asynccontextmanager
    async def create(
        self,
        override: BybitConnectionSettings | None = None,
    ) -> AsyncIterator[BybitTradingAdapter]:
        settings = override or self._settings_store.load().bybit
        adapter = BybitTradingAdapter(
            ExchangeTradingConfig(
                enabled=settings.enabled,
                credentials=ExchangeCredentials(
                    api_key=settings.api_key,
                    secret_key=settings.secret_key,
                ),
            ),
        )
        try:
            yield adapter
        finally:
            await adapter.close()
