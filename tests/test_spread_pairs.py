from datetime import UTC, datetime
from decimal import Decimal

from app.services.spreads.calculator import SpreadResult
from app.services.spreads.pairs import (
    normalize_exchange_pair,
    pair_row_key,
    select_best_by_exchange_pair,
)


def spread(buy: str, sell: str, pct: str) -> SpreadResult:
    return SpreadResult(
        asset_id=7,
        buy_exchange=buy,
        sell_exchange=sell,
        buy_exchange_id=1,
        sell_exchange_id=2,
        buy_price=Decimal("100"),
        sell_price=Decimal("101"),
        delta_abs=Decimal("1"),
        delta_pct=Decimal(pct),
        observed_at=datetime.now(UTC),
    )


def test_pair_key_is_stable_when_direction_flips() -> None:
    assert normalize_exchange_pair("bybit", "binance") == ("binance", "bybit")
    assert pair_row_key(7, "bybit", "binance") == "7:binance:bybit"


def test_best_direction_is_selected_inside_exchange_pair() -> None:
    result = select_best_by_exchange_pair(
        [spread("binance", "bybit", "0.4"), spread("bybit", "binance", "-0.2")]
    )
    selected = result[("binance", "bybit")]
    assert selected.buy_exchange == "binance"
    assert selected.sell_exchange == "bybit"
