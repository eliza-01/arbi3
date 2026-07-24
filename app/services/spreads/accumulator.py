import asyncio
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.services.spreads.calculator import SpreadResult


@dataclass(slots=True)
class AccumulatedPeak:
    asset_id: int
    buy_exchange_id: int
    sell_exchange_id: int
    bucket_start: datetime
    delta_pct: Decimal
    delta_abs: Decimal
    observed_at: datetime


class SpreadAccumulator:
    def __init__(self) -> None:
        self._items: dict[tuple[int, int, int, datetime], AccumulatedPeak] = {}
        self._lock = asyncio.Lock()

    async def add(self, spread: SpreadResult) -> None:
        bucket_start = spread.observed_at.replace(second=0, microsecond=0)
        key = (
            spread.asset_id,
            spread.buy_exchange_id,
            spread.sell_exchange_id,
            bucket_start,
        )
        async with self._lock:
            current = self._items.get(key)
            if current is None or spread.delta_pct > current.delta_pct:
                self._items[key] = AccumulatedPeak(
                    asset_id=spread.asset_id,
                    buy_exchange_id=spread.buy_exchange_id,
                    sell_exchange_id=spread.sell_exchange_id,
                    bucket_start=bucket_start,
                    delta_pct=spread.delta_pct,
                    delta_abs=spread.delta_abs,
                    observed_at=spread.observed_at,
                )

    async def drain(self) -> list[AccumulatedPeak]:
        async with self._lock:
            items = list(self._items.values())
            self._items.clear()
        return items
