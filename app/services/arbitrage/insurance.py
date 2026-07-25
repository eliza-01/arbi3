import asyncio
import time


async def wait_for_both_legs(
    *,
    buy_adapter,
    sell_adapter,
    buy_symbol: str,
    sell_symbol: str,
    expected_buy: float,
    expected_sell: float,
    deadline: float,
) -> tuple[float, float]:
    latest = (0.0, 0.0)
    while time.monotonic() < deadline:
        buy_positions, sell_positions = await asyncio.gather(
            buy_adapter.positions(buy_symbol),
            sell_adapter.positions(sell_symbol),
        )
        latest = (
            position_quantity(buy_positions, "long"),
            position_quantity(sell_positions, "short"),
        )
        buy_ready = latest[0] > 0 and (
            expected_buy <= 0 or latest[0] >= expected_buy * 0.999
        )
        sell_ready = latest[1] > 0 and (
            expected_sell <= 0 or latest[1] >= expected_sell * 0.999
        )
        if buy_ready and sell_ready:
            return latest
        await asyncio.sleep(min(0.2, max(deadline - time.monotonic(), 0.01)))
    return latest


def position_quantity(positions, direction: str) -> float:
    return sum(
        float(position.quantity)
        for position in positions
        if position.direction == direction
    )
