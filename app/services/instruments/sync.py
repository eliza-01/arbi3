import logging

from app.db.session import SessionFactory
from app.exchanges.registry import ExchangeRegistry
from app.repositories.assets import AssetRepository
from app.repositories.exchanges import ExchangeRepository
from app.services.instruments.catalog import InstrumentCatalog

logger = logging.getLogger(__name__)


class InstrumentSyncService:
    def __init__(
        self,
        registry: ExchangeRegistry,
        exchanges: ExchangeRepository,
        assets: AssetRepository,
        catalog: InstrumentCatalog,
    ) -> None:
        self._registry = registry
        self._exchanges = exchanges
        self._assets = assets
        self._catalog = catalog

    async def execute(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for adapter in self._registry.all():
            try:
                instruments = await adapter.fetch_instruments()
                async with SessionFactory() as session:
                    exchange = await self._exchanges.ensure(session, adapter.code, adapter.name)
                    await self._assets.mark_exchange_symbols_inactive(session, exchange.id)
                    for instrument in instruments:
                        await self._assets.upsert_instrument(session, exchange.id, instrument)
                    await session.commit()
                counts[adapter.code] = len(instruments)
                logger.info("Synced %s instruments from %s", len(instruments), adapter.code)
            except Exception:
                logger.exception("Instrument sync failed for %s; keeping previous data", adapter.code)
                counts[adapter.code] = 0

        async with SessionFactory() as session:
            await self._assets.refresh_comparable_flags(session)
            await session.commit()
        await self._catalog.reload()
        return counts
