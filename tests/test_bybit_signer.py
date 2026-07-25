from app.exchanges.bybit.trading_signer import json_body, query_string, signature


def test_bybit_get_signature_matches_official_example() -> None:
    payload = query_string(
        {"category": "option", "symbol": "BTC-29JUL22-25000-C"},
    )
    assert payload == "category=option&symbol=BTC-29JUL22-25000-C"
    assert signature(
        "testsecret",
        1658384314791,
        "XXXXXXXXXX",
        5000,
        payload,
    ) == "d54ef4b8574c386efbbd899379e8a18667712f78f21f2efa7dbf7743094f483c"


def test_bybit_post_body_is_compact_and_deterministic() -> None:
    assert json_body({"category": "linear", "symbol": "BTCUSDT"}) == (
        '{"category":"linear","symbol":"BTCUSDT"}'
    )
