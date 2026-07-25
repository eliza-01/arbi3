from collections.abc import Iterable

from app.services.spreads.calculator import SpreadResult


def normalize_exchange_pair(left: str, right: str) -> tuple[str, str]:
    if left == right:
        raise ValueError("Exchange pair must contain two different exchanges")
    return tuple(sorted((left, right)))  # type: ignore[return-value]


def pair_row_key(asset_id: int, left: str, right: str) -> str:
    exchange_a, exchange_b = normalize_exchange_pair(left, right)
    return f"{asset_id}:{exchange_a}:{exchange_b}"


def select_best_by_exchange_pair(
    spreads: Iterable[SpreadResult],
) -> dict[tuple[str, str], SpreadResult]:
    result: dict[tuple[str, str], SpreadResult] = {}
    for spread in spreads:
        key = normalize_exchange_pair(spread.buy_exchange, spread.sell_exchange)
        current = result.get(key)
        if current is None or spread.delta_pct > current.delta_pct:
            result[key] = spread
    return result
