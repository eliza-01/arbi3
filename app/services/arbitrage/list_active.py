from app.db.session import SessionFactory
from app.repositories.arbitrage_trades import ArbitrageTradeRepository
from app.services.arbitrage.serialization import serialize_trade
from app.services.instruments.catalog import InstrumentCatalog


class ListActiveArbitrageTradesService:
    def __init__(
        self,
        repository: ArbitrageTradeRepository,
        catalog: InstrumentCatalog,
    ) -> None:
        self._repository = repository
        self._catalog = catalog

    async def execute(self) -> list[dict]:
        async with SessionFactory() as session:
            trades = await self._repository.list_active(session)
        return [serialize_trade(trade, self._catalog) for trade in trades]
