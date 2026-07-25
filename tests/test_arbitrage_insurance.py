import time

import pytest

from app.exchanges.trading.models import Position
from app.services.arbitrage.insurance import wait_for_both_legs


class FakeAdapter:
    def __init__(self, direction: str, quantities: list[float]) -> None:
        self.direction = direction
        self.quantities = list(quantities)

    async def positions(self, symbol: str):
        quantity = self.quantities.pop(0) if len(self.quantities) > 1 else self.quantities[0]
        if quantity <= 0:
            return []
        return [Position(symbol=symbol, direction=self.direction, quantity=quantity)]


@pytest.mark.asyncio
async def test_insurance_waits_until_both_legs_are_visible() -> None:
    buy = FakeAdapter("long", [0, 0.5])
    sell = FakeAdapter("short", [0.5, 0.5])
    quantities = await wait_for_both_legs(
        buy_adapter=buy,
        sell_adapter=sell,
        buy_symbol="BTCUSDT",
        sell_symbol="BTCUSDT",
        expected_buy=0.5,
        expected_sell=0.5,
        deadline=time.monotonic() + 1,
    )
    assert quantities == (0.5, 0.5)


@pytest.mark.asyncio
async def test_insurance_returns_exposed_leg_at_deadline() -> None:
    buy = FakeAdapter("long", [0.5])
    sell = FakeAdapter("short", [0])
    quantities = await wait_for_both_legs(
        buy_adapter=buy,
        sell_adapter=sell,
        buy_symbol="BTCUSDT",
        sell_symbol="BTCUSDT",
        expected_buy=0.5,
        expected_sell=0.5,
        deadline=time.monotonic() + 0.03,
    )
    assert quantities[0] == 0.5
    assert quantities[1] == 0
