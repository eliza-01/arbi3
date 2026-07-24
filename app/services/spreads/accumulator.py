import asyncio
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.services.spreads.calculator import SpreadResult


@dataclass(slots=True)
class AccumulatedSpreadBucket:
    asset_id: int
    buy_exchange_id: int
    sell_exchange_id: int
    bucket_start: datetime
    max_delta_pct: Decimal
    max_delta_abs: Decimal
    max_observed_at: datetime
    min_delta_pct: Decimal
    min_delta_abs: Decimal
    min_observed_at: datetime


class SpreadAccumulator:
    def __init__(self) -> None:
        self._items: dict[tuple[int, int, int, datetime], AccumulatedSpreadBucket] = {}
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
            if current is None:
                self._items[key] = AccumulatedSpreadBucket(
                    asset_id=spread.asset_id,
                    buy_exchange_id=spread.buy_exchange_id,
                    sell_exchange_id=spread.sell_exchange_id,
                    bucket_start=bucket_start,
                    max_delta_pct=spread.delta_pct,
                    max_delta_abs=spread.delta_abs,
                    max_observed_at=spread.observed_at,
                    min_delta_pct=spread.delta_pct,
                    min_delta_abs=spread.delta_abs,
                    min_observed_at=spread.observed_at,
                )
                return

            if spread.delta_pct > current.max_delta_pct:
                current.max_delta_pct = spread.delta_pct
                current.max_delta_abs = spread.delta_abs
                current.max_observed_at = spread.observed_at
            if spread.delta_pct < current.min_delta_pct:
                current.min_delta_pct = spread.delta_pct
                current.min_delta_abs = spread.delta_abs
                current.min_observed_at = spread.observed_at

    async def drain(self) -> list[AccumulatedSpreadBucket]:
        async with self._lock:
            items = list(self._items.values())
            self._items.clear()
        return items
