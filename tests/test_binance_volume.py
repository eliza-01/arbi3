import pytest

from app.exchanges.binance.volume import calculate_volume, ticker_price
from app.exchanges.trading.errors import ExchangeRequestError


CONTRACT = {
    "filters": [
        {
            "filterType": "MARKET_LOT_SIZE",
            "minQty": "0.001",
            "maxQty": "1000",
            "stepSize": "0.001",
        },
        {"filterType": "MIN_NOTIONAL", "notional": "5"},
    ],
}


def test_volume_rounds_down_and_up_by_market_step() -> None:
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
    assert down.rounded_amount_usdt == pytest.approx(9)
    assert up.quantity == pytest.approx(0.004)
    assert up.rounded_amount_usdt == pytest.approx(12)


def test_volume_respects_min_notional() -> None:
    result = calculate_volume(
        symbol="BTCUSDT",
        amount_usdt=1,
        rounding="down",
        contract=CONTRACT,
        price=3000,
        side="buy",
    )

    assert result.quantity == pytest.approx(0.002)
    assert result.rounded_amount_usdt == pytest.approx(6)


def test_ticker_uses_only_ask_for_buy_and_bid_for_sell() -> None:
    ticker = {"askPrice": "101", "bidPrice": "99", "lastPrice": "500"}
    assert ticker_price(ticker, "buy") == 101
    assert ticker_price(ticker, "sell") == 99

    with pytest.raises(ExchangeRequestError):
        ticker_price({"lastPrice": "500"}, "buy")
