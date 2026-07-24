import asyncio
from datetime import UTC, datetime, timedelta

from app.core.config import settings
from app.db.session import SessionFactory
from app.repositories.spread_buckets import SpreadBucketRepository
from app.repositories.spread_peaks import SpreadPeakRepository
from app.services.spreads.accumulator import SpreadAccumulator


class SpreadPersistenceService:
    def __init__(
        self,
        accumulator: SpreadAccumulator,
        buckets: SpreadBucketRepository,
        peaks: SpreadPeakRepository,
    ) -> None:
        self._accumulator = accumulator
        self._buckets = buckets
        self._peaks = peaks
        self._stop = asyncio.Event()

    def stop(self) -> None:
        self._stop.set()

    async def run(self) -> None:
        while not self._stop.is_set():
            try:
                await asyncio.wait_for(
                    self._stop.wait(), timeout=settings.spread_bucket_flush_seconds
                )
            except TimeoutError:
                pass
            await self.flush()

    async def flush(self) -> None:
        items = await self._accumulator.drain()
        if not items:
            return
        now = datetime.now(UTC)
        bucket_rows = [
            {
                "asset_id": item.asset_id,
                "buy_exchange_id": item.buy_exchange_id,
                "sell_exchange_id": item.sell_exchange_id,
                "bucket_start": item.bucket_start,
                "max_delta_pct": item.max_delta_pct,
                "max_delta_abs": item.max_delta_abs,
                "observed_at": item.max_observed_at,
                "min_delta_pct": item.min_delta_pct,
                "min_delta_abs": item.min_delta_abs,
                "min_observed_at": item.min_observed_at,
            }
            for item in items
        ]
        all_time_rows = [
            {
                "asset_id": item.asset_id,
                "buy_exchange_id": item.buy_exchange_id,
                "sell_exchange_id": item.sell_exchange_id,
                "all_time_delta_pct": item.max_delta_pct,
                "all_time_at": item.max_observed_at,
                "all_time_min_delta_pct": item.min_delta_pct,
                "all_time_min_at": item.min_observed_at,
                "updated_at": now,
            }
            for item in items
        ]
        cutoff = now - timedelta(hours=settings.spread_bucket_retention_hours)
        async with SessionFactory() as session:
            await self._buckets.upsert_many(session, bucket_rows)
            await self._peaks.upsert_all_time_extrema(session, all_time_rows)
            await self._buckets.delete_older_than(session, cutoff)
            await session.commit()
