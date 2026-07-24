import asyncio
import logging

from app.exchanges.contracts import ExchangeAdapter
from app.services.instruments.catalog import InstrumentCatalog
from app.services.quotes.store import QuoteStore
from app.services.runtime.state import RuntimeState

logger = logging.getLogger(__name__)


class ExchangeQuoteCollector:
    def __init__(
        self,
        adapter: ExchangeAdapter,
        symbols: set[str],
        catalog: InstrumentCatalog,
        quote_store: QuoteStore,
        runtime: RuntimeState,
    ) -> None:
        self._adapter = adapter
        self._symbols = symbols
        self._catalog = catalog
        self._quote_store = quote_store
        self._runtime = runtime

    async def run(self) -> None:
        while True:
            try:
                logger.info("Starting %s WebSocket for %s symbols", self._adapter.code, len(self._symbols))
                async for quote in self._adapter.stream_quotes(self._symbols):
                    await self._store(quote)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("%s WebSocket failed; switching to polling", self._adapter.code)
                await self._poll_for_retry_window()

    async def _poll_for_retry_window(self) -> None:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + 30
        while loop.time() < deadline:
            snapshot = await self._runtime.snapshot()
            try:
                quotes = await self._adapter.poll_quotes(self._symbols)
                for quote in quotes:
                    await self._store(quote)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("%s polling failed", self._adapter.code)
            await asyncio.sleep(max(snapshot.interval_ms / 1000, 1.0))

    async def _store(self, quote) -> None:
        asset_id = self._catalog.asset_id_for(quote.exchange_code, quote.symbol)
        if asset_id is not None:
            await self._quote_store.put(asset_id, quote)
