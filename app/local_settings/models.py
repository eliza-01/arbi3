from dataclasses import asdict, dataclass, field
from typing import Any, Literal

RoundingMode = Literal["down", "up"]


@dataclass(slots=True)
class BinanceConnectionSettings:
    enabled: bool = False
    api_key: str = ""
    secret_key: str = ""


@dataclass(slots=True)
class BybitConnectionSettings:
    enabled: bool = False
    api_key: str = ""
    secret_key: str = ""


@dataclass(slots=True)
class TradingSettings:
    position_usdt: float = 10.0
    leverage: int = 1
    rounding: RoundingMode = "down"
    insurance_seconds: float = 5.0


@dataclass(slots=True)
class LocalSettings:
    binance: BinanceConnectionSettings = field(default_factory=BinanceConnectionSettings)
    bybit: BybitConnectionSettings = field(default_factory=BybitConnectionSettings)
    trading: TradingSettings = field(default_factory=TradingSettings)

    def to_dict(self, hide_secrets: bool = False) -> dict[str, Any]:
        data = asdict(self)
        if hide_secrets:
            data["binance"] = _public_exchange_settings(
                self.binance.enabled,
                self.binance.api_key,
                self.binance.secret_key,
            )
            data["bybit"] = _public_exchange_settings(
                self.bybit.enabled,
                self.bybit.api_key,
                self.bybit.secret_key,
            )
        return data


def settings_from_dict(data: dict[str, Any]) -> LocalSettings:
    binance_raw = data.get("binance") if isinstance(data.get("binance"), dict) else {}
    bybit_raw = data.get("bybit") if isinstance(data.get("bybit"), dict) else {}
    trading_raw = data.get("trading") if isinstance(data.get("trading"), dict) else {}
    rounding = "up" if trading_raw.get("rounding") == "up" else "down"
    return LocalSettings(
        binance=BinanceConnectionSettings(
            enabled=_bool(binance_raw.get("enabled"), False),
            api_key=str(binance_raw.get("api_key") or "").strip(),
            secret_key=str(binance_raw.get("secret_key") or "").strip(),
        ),
        bybit=BybitConnectionSettings(
            enabled=_bool(bybit_raw.get("enabled"), False),
            api_key=str(bybit_raw.get("api_key") or "").strip(),
            secret_key=str(bybit_raw.get("secret_key") or "").strip(),
        ),
        trading=TradingSettings(
            position_usdt=_positive_float(trading_raw.get("position_usdt"), 10.0),
            leverage=_bounded_int(trading_raw.get("leverage"), 1, 1, 125),
            rounding=rounding,
            insurance_seconds=_bounded_float(
                trading_raw.get("insurance_seconds"),
                5.0,
                1.0,
                60.0,
            ),
        ),
    )


def _public_exchange_settings(
    enabled: bool,
    api_key: str,
    secret_key: str,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "enabled": enabled,
        "api_key_masked": _mask(api_key),
        "api_key_configured": bool(api_key),
        "secret_key_configured": bool(secret_key),
    }
    return result


def _mask(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def _bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _positive_float(value: Any, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _non_negative_float(value: Any, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 0 else default


def _bounded_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return min(max(parsed, minimum), maximum)


def _bounded_float(value: Any, default: float, minimum: float, maximum: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if parsed < minimum or parsed > maximum:
        return default
    return parsed
