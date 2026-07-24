from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.services.spreads.accumulator import SpreadAccumulator
from app.services.spreads.calculator import SpreadResult


def make_spread(delta_pct: str, observed_at: datetime) -> SpreadResult:
    return SpreadResult(
        asset_id=1,
        buy_exchange="binance",
        sell_exchange="bybit",
        buy_exchange_id=1,
        sell_exchange_id=2,
        buy_price=Decimal("100"),
        sell_price=Decimal("100") + Decimal(delta_pct),
        delta_abs=Decimal(delta_pct),
        delta_pct=Decimal(delta_pct),
        observed_at=observed_at,
    )


@pytest.mark.asyncio
async def test_accumulates_minimum_and_maximum_in_minute_bucket() -> None:
    accumulator = SpreadAccumulator()
    observed_at = datetime.now(UTC).replace(second=10, microsecond=0)

    await accumulator.add(make_spread("1.5", observed_at))
    await accumulator.add(make_spread("0.2", observed_at + timedelta(seconds=10)))
    await accumulator.add(make_spread("2.1", observed_at + timedelta(seconds=20)))

    items = await accumulator.drain()

    assert len(items) == 1
    assert items[0].min_delta_pct == Decimal("0.2")
    assert items[0].max_delta_pct == Decimal("2.1")
