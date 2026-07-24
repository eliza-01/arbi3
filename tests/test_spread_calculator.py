from datetime import UTC, datetime
from decimal import Decimal

from app.services.instruments.contracts import CatalogAsset
from app.services.quotes.store import StoredQuote
from app.services.spreads.arbitrage import select_best_arbitrage
from app.services.spreads.calculator import calculate_directional_spreads


def make_asset() -> CatalogAsset:
    return CatalogAsset(
        id=1,
        base_asset="BTC",
        quote_asset="USDT",
        contract_type="PERPETUAL",
        symbols={"binance": "BTCUSDT", "bybit": "BTCUSDT"},
        exchange_ids={"binance": 1, "bybit": 2},
    )


def test_calculates_both_executable_directions() -> None:
    now = datetime.now(UTC)
    quotes = {
        "binance": StoredQuote(Decimal("100"), Decimal("101"), Decimal("100.5"), now),
        "bybit": StoredQuote(Decimal("103"), Decimal("104"), Decimal("103.5"), now),
    }

    spreads = calculate_directional_spreads(make_asset(), quotes)

    assert len(spreads) == 2
    best = select_best_arbitrage(spreads)
    assert best is not None
    assert best.buy_exchange == "binance"
    assert best.sell_exchange == "bybit"
    assert best.buy_price == Decimal("101")
    assert best.sell_price == Decimal("103")
    assert best.delta_abs == Decimal("2")


def test_selects_route_by_ask_and_bid_not_last_price() -> None:
    now = datetime.now(UTC)
    quotes = {
        "binance": StoredQuote(Decimal("102"), Decimal("103"), Decimal("90"), now),
        "bybit": StoredQuote(Decimal("100"), Decimal("101"), Decimal("110"), now),
    }

    best = select_best_arbitrage(calculate_directional_spreads(make_asset(), quotes))

    assert best is not None
    assert best.buy_exchange == "bybit"
    assert best.buy_price == Decimal("101")
    assert best.sell_exchange == "binance"
    assert best.sell_price == Decimal("102")
    assert best.delta_abs == Decimal("1")


def test_skips_non_positive_execution_prices() -> None:
    now = datetime.now(UTC)
    quotes = {
        "binance": StoredQuote(Decimal("100"), Decimal("0"), Decimal("100"), now),
        "bybit": StoredQuote(Decimal("103"), Decimal("104"), Decimal("103.5"), now),
    }

    spreads = calculate_directional_spreads(make_asset(), quotes)

    assert len(spreads) == 1
    assert spreads[0].buy_exchange == "bybit"
    assert spreads[0].sell_exchange == "binance"
