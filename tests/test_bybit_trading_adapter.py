import pytest

from app.exchanges.bybit.trading_adapter import BybitTradingAdapter
from app.exchanges.bybit.trading_constants import (
    CREATE_ORDER,
    INSTRUMENTS_INFO,
    POSITION_LIST,
    SET_LEVERAGE,
    TICKERS,
)
from app.exchanges.trading.models import (
    ClosePositionRequest,
    ExchangeCredentials,
    ExchangeTradingConfig,
    OpenPositionRequest,
)


class FakeClient:
    def __init__(self, hedge: bool = False, open_position: bool = False) -> None:
        self.hedge = hedge
        self.open_position = open_position
        self.posts: list[tuple[str, dict]] = []

    async def close(self) -> None:
        return None

    async def public_get(self, endpoint: str, params=None):
        if endpoint == INSTRUMENTS_INFO:
            return {
                "retCode": 0,
                "result": {
                    "list": [
                        {
                            "symbol": "BTCUSDT",
                            "status": "Trading",
                            "contractType": "LinearPerpetual",
                            "leverageFilter": {"maxLeverage": "100"},
                            "lotSizeFilter": {
                                "minOrderQty": "0.01",
                                "maxMktOrderQty": "100",
                                "qtyStep": "0.01",
                                "minNotionalValue": "5",
                            },
                        },
                    ],
                },
            }
        if endpoint == TICKERS:
            return {
                "retCode": 0,
                "result": {
                    "list": [
                        {"symbol": "BTCUSDT", "ask1Price": "101", "bid1Price": "99", "lastPrice": "500"},
                    ],
                },
            }
        return {"retCode": 0, "result": {}}

    async def signed_get(self, endpoint: str, params=None):
        if endpoint == POSITION_LIST:
            if self.open_position:
                return {
                    "retCode": 0,
                    "result": {
                        "list": [
                            {
                                "symbol": "BTCUSDT",
                                "side": "Buy",
                                "size": "0.50",
                                "avgPrice": "100",
                                "unrealisedPnl": "1",
                                "positionIdx": 1 if self.hedge else 0,
                            },
                        ],
                    },
                }
            indices = [1, 2] if self.hedge else [0]
            return {
                "retCode": 0,
                "result": {
                    "list": [
                        {"symbol": "BTCUSDT", "side": "", "size": "0", "positionIdx": index}
                        for index in indices
                    ],
                },
            }
        return {"retCode": 0, "result": {}}

    async def signed_post(self, endpoint: str, payload=None):
        body = dict(payload or {})
        self.posts.append((endpoint, body))
        if endpoint == SET_LEVERAGE:
            return {"retCode": 0, "result": {}}
        if endpoint == CREATE_ORDER:
            return {"retCode": 0, "result": {"orderId": "abc"}}
        return {"retCode": 0, "result": {}}


def adapter(client: FakeClient) -> BybitTradingAdapter:
    return BybitTradingAdapter(
        ExchangeTradingConfig(True, ExchangeCredentials("key", "secret")),
        client=client,
    )


@pytest.mark.asyncio
async def test_bybit_open_long_uses_ask_buy_and_hedge_index() -> None:
    client = FakeClient(hedge=True)
    result = await adapter(client).open_position(
        OpenPositionRequest("BTCUSDT", "long", 100, 5, "down"),
    )
    order = next(body for endpoint, body in client.posts if endpoint == CREATE_ORDER)
    assert order["side"] == "Buy"
    assert order["orderType"] == "Market"
    assert order["positionIdx"] == 1
    assert order["qty"] == "0.99"
    assert result.raw["calculation"]["price"] == 101


@pytest.mark.asyncio
async def test_bybit_open_short_uses_bid_sell_and_one_way_index() -> None:
    client = FakeClient(hedge=False)
    result = await adapter(client).open_position(
        OpenPositionRequest("BTCUSDT", "short", 100, 5, "down"),
    )
    order = next(body for endpoint, body in client.posts if endpoint == CREATE_ORDER)
    assert order["side"] == "Sell"
    assert order["positionIdx"] == 0
    assert order["qty"] == "1.01"
    assert result.raw["calculation"]["price"] == 99


@pytest.mark.asyncio
async def test_bybit_close_long_is_reduce_only_sell() -> None:
    client = FakeClient(hedge=True, open_position=True)
    await adapter(client).close_position(
        ClosePositionRequest("BTCUSDT", "long"),
    )
    order = next(body for endpoint, body in client.posts if endpoint == CREATE_ORDER)
    assert order["side"] == "Sell"
    assert order["reduceOnly"] is True
    assert order["positionIdx"] == 1
    assert order["qty"] == "0.5"


@pytest.mark.asyncio
async def test_bybit_close_can_use_exact_arbitrage_quantity() -> None:
    client = FakeClient(hedge=True, open_position=True)
    await adapter(client).close_position(
        ClosePositionRequest("BTCUSDT", "long", quantity=0.2),
    )
    order = next(body for endpoint, body in client.posts if endpoint == CREATE_ORDER)
    assert order["side"] == "Sell"
    assert order["reduceOnly"] is True
    assert order["qty"] == "0.2"
