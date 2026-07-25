import pytest

from app.exchanges.binance.trading_adapter import BinanceTradingAdapter
from app.exchanges.binance.trading_constants import (
    BOOK_TICKER,
    CHANGE_LEVERAGE,
    EXCHANGE_INFO,
    NEW_ORDER,
    POSITION_MODE,
    POSITION_RISK,
)
from app.exchanges.trading.models import (
    ClosePositionRequest,
    ExchangeCredentials,
    ExchangeTradingConfig,
    OpenPositionRequest,
)


class FakeClient:
    def __init__(self, open_position: bool = False) -> None:
        self.open_position = open_position
        self.posts: list[tuple[str, dict]] = []

    async def close(self) -> None:
        return None

    async def public_get(self, endpoint: str, params=None):
        if endpoint == EXCHANGE_INFO:
            return {
                "symbols": [
                    {
                        "symbol": "BTCUSDT",
                        "filters": [
                            {
                                "filterType": "MARKET_LOT_SIZE",
                                "minQty": "0.01",
                                "maxQty": "100",
                                "stepSize": "0.01",
                            },
                            {"filterType": "MIN_NOTIONAL", "notional": "5"},
                        ],
                    },
                ],
            }
        if endpoint == BOOK_TICKER:
            return {"askPrice": "101", "bidPrice": "99", "lastPrice": "500"}
        return {}

    async def signed_get(self, endpoint: str, params=None):
        if endpoint == POSITION_MODE:
            return {"dualSidePosition": False}
        if endpoint == POSITION_RISK and self.open_position:
            return [{
                "symbol": "BTCUSDT",
                "positionAmt": "0.50",
                "positionSide": "BOTH",
                "entryPrice": "100",
                "unRealizedProfit": "1",
            }]
        return []

    async def signed_post(self, endpoint: str, params=None):
        payload = dict(params or {})
        self.posts.append((endpoint, payload))
        if endpoint == CHANGE_LEVERAGE:
            return {"leverage": payload["leverage"]}
        if endpoint == NEW_ORDER:
            return {"orderId": 123}
        return {}


def adapter(client: FakeClient) -> BinanceTradingAdapter:
    return BinanceTradingAdapter(
        ExchangeTradingConfig(
            enabled=True,
            credentials=ExchangeCredentials("key", "secret"),
        ),
        client=client,
    )


@pytest.mark.asyncio
async def test_open_long_uses_ask_and_buy_market_order() -> None:
    client = FakeClient()
    result = await adapter(client).open_position(
        OpenPositionRequest("BTCUSDT", "long", 100, 5, "down"),
    )

    order = next(payload for endpoint, payload in client.posts if endpoint == NEW_ORDER)
    assert order["side"] == "BUY"
    assert order["type"] == "MARKET"
    assert order["quantity"] == "0.99"
    assert result.raw["calculation"]["price"] == 101


@pytest.mark.asyncio
async def test_open_short_uses_bid_and_sell_market_order() -> None:
    client = FakeClient()
    result = await adapter(client).open_position(
        OpenPositionRequest("BTCUSDT", "short", 100, 5, "down"),
    )

    order = next(payload for endpoint, payload in client.posts if endpoint == NEW_ORDER)
    assert order["side"] == "SELL"
    assert order["type"] == "MARKET"
    assert order["quantity"] == "1.01"
    assert result.raw["calculation"]["price"] == 99


@pytest.mark.asyncio
async def test_binance_close_can_use_exact_arbitrage_quantity() -> None:
    client = FakeClient(open_position=True)
    await adapter(client).close_position(
        ClosePositionRequest("BTCUSDT", "long", quantity=0.2),
    )
    order = next(payload for endpoint, payload in client.posts if endpoint == NEW_ORDER)
    assert order["side"] == "SELL"
    assert order["reduceOnly"] == "true"
    assert order["quantity"] == "0.2"
