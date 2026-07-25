from app.local_settings.store import LocalSettingsStore


def test_local_settings_preserve_secrets_and_hide_them_from_public_response(tmp_path) -> None:
    store = LocalSettingsStore(str(tmp_path / "settings.json"))
    store.update(
        {
            "binance": {"enabled": True, "api_key": "abcdefgh12345678", "secret_key": "secret"},
            "bybit": {"enabled": True, "api_key": "bybit-key-1234", "secret_key": "bybit-secret"},
            "trading": {"position_usdt": 25, "leverage": 5, "rounding": "up", "insurance_seconds": 7.5},
        },
    )

    settings = store.load()
    assert settings.binance.api_key == "abcdefgh12345678"
    assert settings.bybit.api_key == "bybit-key-1234"
    assert settings.trading.position_usdt == 25
    assert settings.trading.leverage == 5
    assert settings.trading.rounding == "up"
    assert settings.trading.insurance_seconds == 7.5

    public = settings.to_dict(hide_secrets=True)
    assert "api_key" not in public["binance"]
    assert "secret_key" not in public["binance"]
    assert public["binance"]["api_key_configured"] is True
    assert "api_key" not in public["bybit"]
    assert "secret_key" not in public["bybit"]
    assert public["bybit"]["api_key_configured"] is True
