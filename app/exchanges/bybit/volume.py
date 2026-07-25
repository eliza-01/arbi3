from decimal import Decimal, InvalidOperation, ROUND_DOWN, ROUND_UP
from typing import Any

from app.exchanges.binance.volume import normalize_symbol, plain_decimal
from app.exchanges.trading.errors import ExchangeRequestError
from app.exchanges.trading.models import NotionalRounding, VolumeCalculation


def ticker_price(item: dict[str, Any], side: str) -> float:
    key = "ask1Price" if side == "buy" else "bid1Price"
    value = _decimal(item.get(key))
    if value > 0:
        return float(value)
    title = "ask" if side == "buy" else "bid"
    raise ExchangeRequestError(f"Bybit не вернула текущую цену {title}")


def calculate_volume(
    *,
    symbol: str,
    amount_usdt: float,
    rounding: NotionalRounding,
    contract: dict[str, Any],
    price: float,
    side: str,
) -> VolumeCalculation:
    normalized = normalize_symbol(symbol)
    notional = _decimal(amount_usdt)
    price_value = _decimal(price)
    if notional <= 0:
        raise ExchangeRequestError("Объём позиции должен быть больше 0 USDT")
    if price_value <= 0:
        raise ExchangeRequestError(f"Нет текущей цены для {normalized}")

    lot = contract.get("lotSizeFilter") if isinstance(contract.get("lotSizeFilter"), dict) else {}
    minimum = _decimal(lot.get("minOrderQty") or 0)
    maximum = _decimal(lot.get("maxMktOrderQty") or lot.get("maxOrderQty") or 0)
    step = _decimal(lot.get("qtyStep") or 0)
    min_notional = _decimal(lot.get("minNotionalValue") or 0)

    raw = notional / price_value
    rounded = _round_to_step(raw, step, ROUND_UP if rounding == "up" else ROUND_DOWN)
    required = minimum
    if min_notional > 0:
        required = max(required, min_notional / price_value)
    if rounded < required:
        rounded = _round_to_step(required, step, ROUND_UP)

    if rounded <= 0:
        raise ExchangeRequestError(
            f"Объём {normalized} после округления равен нулю; увеличьте USDT",
        )
    if maximum > 0 and rounded > maximum:
        raise ExchangeRequestError(
            f"Максимальный market-объём для {normalized}: {plain_decimal(maximum)}",
        )

    quantity = float(rounded) if rounded != rounded.to_integral_value() else int(rounded)
    return VolumeCalculation(
        symbol=normalized,
        side="buy" if side == "buy" else "sell",
        requested_amount_usdt=float(notional),
        price=float(price_value),
        quantity=quantity,
        rounded_amount_usdt=float(rounded * price_value),
        rounding=rounding,
        min_quantity=float(minimum) if minimum > 0 else None,
        max_quantity=float(maximum) if maximum > 0 else None,
        quantity_step=float(step) if step > 0 else None,
        min_notional_usdt=float(min_notional) if min_notional > 0 else None,
    )


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def _round_to_step(value: Decimal, step: Decimal, rounding: str) -> Decimal:
    if step <= 0:
        return value
    return (value / step).to_integral_value(rounding=rounding) * step
