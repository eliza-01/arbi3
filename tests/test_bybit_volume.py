import pytest

from app.exchanges.bybit.volume import calculate_volume, ticker_price
from app.exchanges.trading.errors import ExchangeRequestError

CONTRACT = {
    "lotSizeFilter": {
        "minOrderQty": "0.001",
        "maxMktOrderQty": "100",
        "qtyStep": "0.001",
        "minNotionalValue": "5",
    },
}


def test_bybit_volume_rounds_by_qty_step() -> None:
    down = calculate_volume(
        symbol="BTCUSDT",
        amount_usdt=10,
        rounding="down",
        contract=CONTRACT,
        price=3000,
        side="buy",
    )
    up = calculate_volume(
        symbol="BTCUSDT",
        amount_usdt=10,
        rounding="up",
        contract=CONTRACT,
        price=3000,
        side="buy",
    )
    assert down.quantity == pytest.approx(0.003)
    assert up.quantity == pytest.approx(0.004)


def test_bybit_ticker_uses_ask_and_bid_not_last() -> None:
    ticker = {"ask1Price": "101", "bid1Price": "99", "lastPrice": "500"}
    assert ticker_price(ticker, "buy") == 101
    assert ticker_price(ticker, "sell") == 99
    with pytest.raises(ExchangeRequestError):
        ticker_price({"lastPrice": "500"}, "buy")
