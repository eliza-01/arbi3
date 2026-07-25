from decimal import Decimal, InvalidOperation, ROUND_DOWN, ROUND_UP
from typing import Any

from app.exchanges.trading.errors import ExchangeRequestError
from app.exchanges.trading.models import NotionalRounding, VolumeCalculation


def normalize_symbol(symbol: str | None) -> str:
    clean = (symbol or "").strip().upper().replace("/", "").replace("_", "").replace("-", "")
    if not clean:
        raise ExchangeRequestError("Не указан futures-символ")
    return clean


def ticker_price(data: dict[str, Any], side: str) -> float:
    key = "askPrice" if side == "buy" else "bidPrice"
    value = _maybe_float(data.get(key))
    if value is not None and value > 0:
        return value
    price_title = "ask" if side == "buy" else "bid"
    raise ExchangeRequestError(f"Binance не вернула текущую цену {price_title}")


def calculate_volume(
    *,
    symbol: str,
    amount_usdt: float,
    rounding: NotionalRounding,
    contract: dict[str, Any],
    price: float,
    side: str,
) -> VolumeCalculation:
    normalized_symbol = normalize_symbol(symbol)
    notional = _decimal(amount_usdt)
    price_value = _decimal(price)
    if notional <= 0:
        raise ExchangeRequestError("Объём позиции должен быть больше 0 USDT")
    if price_value <= 0:
        raise ExchangeRequestError(f"Нет текущей цены для {normalized_symbol}")

    lot = _filter(contract, "MARKET_LOT_SIZE") or _filter(contract, "LOT_SIZE")
    min_quantity = _decimal(lot.get("minQty") or 0)
    max_quantity = _decimal(lot.get("maxQty") or 0)
    step = _decimal(lot.get("stepSize") or 0)
    min_notional_filter = _filter(contract, "MIN_NOTIONAL")
    min_notional = _decimal(min_notional_filter.get("notional") or 0)

    raw_quantity = notional / price_value
    rounded = _round_to_step(
        raw_quantity,
        step,
        ROUND_UP if rounding == "up" else ROUND_DOWN,
    )

    required_minimum = min_quantity
    if min_notional > 0:
        required_minimum = max(required_minimum, min_notional / price_value)
    if rounded < required_minimum:
        rounded = _round_to_step(required_minimum, step, ROUND_UP)

    if rounded <= 0:
        raise ExchangeRequestError(
            f"Объём {normalized_symbol} после округления равен нулю; выберите округление вверх или увеличьте USDT",
        )
    if max_quantity > 0 and rounded > max_quantity:
        raise ExchangeRequestError(
            f"Максимальный объём для {normalized_symbol}: {_plain_decimal(max_quantity)}",
        )

    quantity_scale = _scale_from_step(step, fallback=8)
    quantity = _json_number(rounded, quantity_scale)
    rounded_amount = rounded * price_value
    return VolumeCalculation(
        symbol=normalized_symbol,
        side="buy" if side == "buy" else "sell",
        requested_amount_usdt=float(notional),
        price=float(price_value),
        quantity=quantity,
        rounded_amount_usdt=float(rounded_amount),
        rounding=rounding,
        min_quantity=float(min_quantity) if min_quantity > 0 else None,
        max_quantity=float(max_quantity) if max_quantity > 0 else None,
        quantity_step=float(step) if step > 0 else None,
        min_notional_usdt=float(min_notional) if min_notional > 0 else None,
    )


def plain_decimal(value: float | int | Decimal) -> str:
    return _plain_decimal(_decimal(value))


def _filter(contract: dict[str, Any], filter_type: str) -> dict[str, Any]:
    filters = contract.get("filters")
    if not isinstance(filters, list):
        return {}
    for item in filters:
        if isinstance(item, dict) and item.get("filterType") == filter_type:
            return item
    return {}


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def _maybe_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _round_to_step(value: Decimal, step: Decimal, rounding: str) -> Decimal:
    if step <= 0:
        return value
    return (value / step).to_integral_value(rounding=rounding) * step


def _scale_from_step(step: Decimal, fallback: int) -> int:
    if step <= 0:
        return fallback
    return max(0, -step.normalize().as_tuple().exponent)


def _json_number(value: Decimal, scale: int) -> float | int:
    if scale == 0:
        return int(value.to_integral_value(rounding=ROUND_DOWN))
    quantized = value.quantize(Decimal(1).scaleb(-scale), rounding=ROUND_DOWN)
    return float(quantized)


def _plain_decimal(value: Decimal) -> str:
    if value == value.to_integral_value():
        return str(int(value))
    return format(value.normalize(), "f")
