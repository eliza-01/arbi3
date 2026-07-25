import asyncio
from datetime import UTC, datetime

from app.services.broadcast.hub import BroadcastHub
from app.services.instruments.catalog import InstrumentCatalog
from app.services.quotes.store import QuoteStore
from app.services.quotes.subscriptions import is_pair_active, select_active_asset_ids
from app.services.runtime.state import RuntimeState
from app.services.spreads.accumulator import SpreadAccumulator
from app.services.spreads.calculator import calculate_directional_spreads
from app.services.spreads.pairs import pair_row_key, select_best_by_exchange_pair


class SpreadEngine:
    def __init__(
        self,
        catalog: InstrumentCatalog,
        quote_store: QuoteStore,
        runtime: RuntimeState,
        accumulator: SpreadAccumulator,
        hub: BroadcastHub,
    ) -> None:
        self._catalog = catalog
        self._quote_store = quote_store
        self._runtime = runtime
        self._accumulator = accumulator
        self._hub = hub
        self._stop = asyncio.Event()

    def stop(self) -> None:
        self._stop.set()

    async def run(self) -> None:
        while not self._stop.is_set():
            runtime = await self._runtime.snapshot()
            active_ids = select_active_asset_ids(
                {asset.id for asset in self._catalog.all()}, runtime
            )
            quote_snapshot = await self._quote_store.snapshot()
            updates: list[dict] = []
            now = datetime.now(UTC)
            stale_after_seconds = max(runtime.interval_ms / 1000 * 5, 60)
            for asset_id, quotes in quote_snapshot.items():
                if asset_id not in active_ids:
                    continue

                asset = self._catalog.get(asset_id)
                fresh_quotes = {
                    code: quote
                    for code, quote in quotes.items()
                    if (now - quote.observed_at).total_seconds() <= stale_after_seconds
                }
                if asset is None or len(fresh_quotes) < 2:
                    continue

                pair_spreads = select_best_by_exchange_pair(
                    calculate_directional_spreads(asset, fresh_quotes)
                )
                for (exchange_a, exchange_b), best in pair_spreads.items():
                    if not is_pair_active(
                        asset.id, exchange_a, exchange_b, runtime
                    ):
                        continue
                    await self._accumulator.add(best)
                    pair_quotes = {
                        code: fresh_quotes[code]
                        for code in (exchange_a, exchange_b)
                        if code in fresh_quotes
                    }
                    updates.append(
                        {
                            "row_key": pair_row_key(asset.id, exchange_a, exchange_b),
                            "asset_id": asset.id,
                            "exchange_a": exchange_a,
                            "exchange_b": exchange_b,
                            "quotes": {
                                code: {
                                    "bid": float(quote.bid),
                                    "ask": float(quote.ask),
                                    "last": float(quote.last),
                                    "observed_at": quote.observed_at.isoformat(),
                                }
                                for code, quote in pair_quotes.items()
                            },
                            "current_spread": {
                                "buy_exchange": best.buy_exchange,
                                "sell_exchange": best.sell_exchange,
                                "buy_price": float(best.buy_price),
                                "sell_price": float(best.sell_price),
                                "delta_abs": float(best.delta_abs),
                                "delta_pct": float(best.delta_pct),
                            },
                        }
                    )
            if updates:
                await self._hub.publish(
                    {
                        "type": "quotes",
                        "timestamp": datetime.now(UTC).isoformat(),
                        "items": updates,
                    }
                )
            try:
                await asyncio.wait_for(
                    self._stop.wait(), timeout=max(runtime.interval_ms / 1000, 0.25)
                )
            except TimeoutError:
                pass
