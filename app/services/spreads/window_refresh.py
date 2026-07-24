import asyncio
from datetime import UTC, datetime, timedelta

from app.core.config import settings
from app.db.session import SessionFactory
from app.repositories.spread_buckets import SpreadBucketRepository
from app.repositories.spread_peaks import SpreadPeakRepository


class SpreadWindowRefreshService:
    def __init__(self, buckets: SpreadBucketRepository, peaks: SpreadPeakRepository) -> None:
        self._buckets = buckets
        self._peaks = peaks
        self._stop = asyncio.Event()

    def stop(self) -> None:
        self._stop.set()

    async def run(self) -> None:
        while not self._stop.is_set():
            await self.refresh()
            try:
                await asyncio.wait_for(
                    self._stop.wait(), timeout=settings.spread_window_refresh_seconds
                )
            except TimeoutError:
                pass

    async def refresh(self) -> None:
        now = datetime.now(UTC)
        async with SessionFactory() as session:
            hour_rows = await self._buckets.window_maxima(session, now - timedelta(hours=1))
            day_rows = await self._buckets.window_maxima(session, now - timedelta(days=1))
            await self._peaks.clear_window(session, "hour")
            await self._peaks.clear_window(session, "day")
            await self._peaks.update_window(session, hour_rows, "hour")
            await self._peaks.update_window(session, day_rows, "day")
            await session.commit()
