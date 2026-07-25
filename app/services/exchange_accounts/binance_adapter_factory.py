from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from app.exchanges.binance.trading_adapter import BinanceTradingAdapter
from app.exchanges.trading.models import ExchangeCredentials, ExchangeTradingConfig
from app.local_settings.models import BinanceConnectionSettings
from app.local_settings.store import LocalSettingsStore


class BinanceTradingAdapterFactory:
    def __init__(self, settings_store: LocalSettingsStore) -> None:
        self._settings_store = settings_store

    @asynccontextmanager
    async def create(
        self,
        override: BinanceConnectionSettings | None = None,
    ) -> AsyncIterator[BinanceTradingAdapter]:
        settings = override or self._settings_store.load().binance
        adapter = BinanceTradingAdapter(
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
