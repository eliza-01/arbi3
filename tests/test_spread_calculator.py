from datetime import UTC, datetime
from decimal import Decimal

from app.services.instruments.contracts import CatalogAsset
from app.services.quotes.store import StoredQuote
from app.services.spreads.calculator import calculate_directional_spreads


def test_calculates_both_directions() -> None:
    asset = CatalogAsset(
        id=1,
        base_asset="BTC",
        quote_asset="USDT",
        contract_type="PERPETUAL",
        symbols={"binance": "BTCUSDT", "bybit": "BTCUSDT"},
        exchange_ids={"binance": 1, "bybit": 2},
    )
    now = datetime.now(UTC)
    quotes = {
        "binance": StoredQuote(Decimal("100"), Decimal("101"), Decimal("100.5"), now),
        "bybit": StoredQuote(Decimal("103"), Decimal("104"), Decimal("103.5"), now),
    }
    spreads = calculate_directional_spreads(asset, quotes)
    assert len(spreads) == 2
    best = max(spreads, key=lambda item: item.delta_pct)
    assert best.buy_exchange == "binance"
    assert best.sell_exchange == "bybit"
    assert best.delta_abs == Decimal("2")
