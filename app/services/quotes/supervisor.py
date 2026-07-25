import asyncio
import logging

from app.exchanges.registry import ExchangeRegistry
from app.services.instruments.catalog import InstrumentCatalog
from app.services.quotes.collector import ExchangeQuoteCollector
from app.services.quotes.store import QuoteStore
from app.services.quotes.subscriptions import (
    select_active_asset_ids,
    select_active_asset_ids_for_exchange,
)
from app.services.runtime.state import RuntimeState

logger = logging.getLogger(__name__)


class CollectorSupervisor:
    def __init__(
        self,
        registry: ExchangeRegistry,
        catalog: InstrumentCatalog,
        quote_store: QuoteStore,
        runtime: RuntimeState,
    ) -> None:
        self._registry = registry
        self._catalog = catalog
        self._quote_store = quote_store
        self._runtime = runtime
        self._restart = asyncio.Event()
        self._stop = asyncio.Event()

    def request_restart(self) -> None:
        self._restart.set()

    def stop(self) -> None:
        self._stop.set()
        self._restart.set()

    async def run(self) -> None:
        while not self._stop.is_set():
            snapshot = await self._runtime.snapshot()
            all_asset_ids = {asset.id for asset in self._catalog.all()}
            active_ids = select_active_asset_ids(all_asset_ids, snapshot)
            await self._quote_store.clear_except(active_ids)

            tasks = []
            for adapter in self._registry.all():
                exchange_asset_ids = select_active_asset_ids_for_exchange(
                    all_asset_ids, adapter.code, snapshot
                )
                symbols = self._catalog.symbols_for(adapter.code, exchange_asset_ids)
                if not symbols:
                    continue
                collector = ExchangeQuoteCollector(
                    adapter, symbols, self._catalog, self._quote_store, self._runtime
                )
                tasks.append(
                    asyncio.create_task(collector.run(), name=f"collector:{adapter.code}")
                )

            self._restart.clear()
            wait_restart = asyncio.create_task(self._restart.wait())
            wait_runtime = asyncio.create_task(self._runtime.changed.wait())
            wait_stop = asyncio.create_task(self._stop.wait())
            _, pending = await asyncio.wait(
                [wait_restart, wait_runtime, wait_stop],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for waiter in pending:
                waiter.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            self._runtime.changed.clear()
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.info("Quote subscriptions rebuilt")
