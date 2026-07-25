import time
from typing import Any

from app.exchanges.binance.trading_client import BinanceFuturesTradingClient
from app.exchanges.binance.trading_constants import (
    ACCOUNT_BALANCE,
    BOOK_TICKER,
    CHANGE_LEVERAGE,
    EXCHANGE_INFO,
    NEW_ORDER,
    PING,
    POSITION_MODE,
    POSITION_RISK,
)
from app.exchanges.binance.volume import (
    calculate_volume,
    normalize_symbol,
    plain_decimal,
    ticker_price,
)
from app.exchanges.trading.errors import (
    ExchangeDisabledError,
    ExchangeNotConfiguredError,
    ExchangeRequestError,
)
from app.exchanges.trading.models import (
    Balance,
    ClosePositionRequest,
    ConnectionStatus,
    ExchangeTradingConfig,
    OpenPositionRequest,
    OrderResult,
    Position,
    VolumeCalculation,
)


class BinanceTradingAdapter:
    code = "binance"
    name = "Binance USDⓈ-M Futures"

    def __init__(
        self,
        config: ExchangeTradingConfig,
        client: BinanceFuturesTradingClient | None = None,
    ) -> None:
        self.config = config
        self.client = client or BinanceFuturesTradingClient(
            config.credentials.api_key,
            config.credentials.secret_key,
        )

    async def close(self) -> None:
        await self.client.close()

    async def status(self) -> ConnectionStatus:
        if not self.config.enabled:
            return ConnectionStatus("disabled", "Подключение отключено")
        if not self.config.credentials.api_key or not self.config.credentials.secret_key:
            return ConnectionStatus("not_configured", "API key и Secret key не настроены")
        try:
            await self.client.public_get(PING)
            await self.client.signed_get(ACCOUNT_BALANCE)
            hedge_mode = await self._hedge_mode()
            position_mode = "hedge" if hedge_mode else "one_way"
            title = "Hedge Mode" if hedge_mode else "One-way Mode"
            return ConnectionStatus("connected", f"Подключено · {title}", position_mode)
        except Exception as exc:
            return ConnectionStatus("error", str(exc))

    async def balance(self, currency: str = "USDT") -> Balance:
        self._ensure_ready()
        items = await self.client.signed_get(ACCOUNT_BALANCE)
        for item in _dict_list(items):
            if str(item.get("asset") or "").upper() != currency.upper():
                continue
            wallet_balance = _float(item.get("balance"))
            unrealized_pnl = _float(item.get("crossUnPnl"))
            return Balance(
                currency=currency.upper(),
                available=_float(item.get("availableBalance")),
                equity=wallet_balance + unrealized_pnl,
                wallet_balance=wallet_balance,
                unrealized_pnl=unrealized_pnl,
            )
        return Balance(
            currency=currency.upper(),
            available=0.0,
            equity=0.0,
            wallet_balance=0.0,
            unrealized_pnl=0.0,
        )

    async def positions(self, symbol: str | None = None) -> list[Position]:
        self._ensure_ready()
        params = {"symbol": normalize_symbol(symbol)} if symbol else None
        data = await self.client.signed_get(POSITION_RISK, params)
        result: list[Position] = []
        for item in _dict_list(data):
            quantity = _float(item.get("positionAmt"))
            if quantity == 0:
                continue
            position_side = str(item.get("positionSide") or "BOTH").upper()
            direction = (
                "long"
                if position_side == "LONG" or (position_side == "BOTH" and quantity > 0)
                else "short"
            )
            result.append(
                Position(
                    symbol=str(item.get("symbol") or ""),
                    direction=direction,
                    quantity=abs(quantity),
                    entry_price=_optional_float(item.get("entryPrice")),
                    unrealized_pnl=_optional_float(item.get("unRealizedProfit")),
                ),
            )
        return result

    async def preview_volume(
        self,
        symbol: str,
        amount_usdt: float,
        rounding: str,
    ) -> dict[str, VolumeCalculation]:
        normalized = normalize_symbol(symbol)
        contract = await self._symbol_info(normalized)
        ticker = await self.client.public_get(BOOK_TICKER, {"symbol": normalized})
        if not isinstance(ticker, dict):
            raise ExchangeRequestError(f"Binance не вернула котировку {normalized}")
        mode = "up" if rounding == "up" else "down"
        return {
            "buy": calculate_volume(
                symbol=normalized,
                amount_usdt=amount_usdt,
                rounding=mode,
                contract=contract,
                price=ticker_price(ticker, "buy"),
                side="buy",
            ),
            "sell": calculate_volume(
                symbol=normalized,
                amount_usdt=amount_usdt,
                rounding=mode,
                contract=contract,
                price=ticker_price(ticker, "sell"),
                side="sell",
            ),
        }

    async def set_leverage(self, symbol: str, leverage: int) -> int:
        self._ensure_ready()
        normalized = normalize_symbol(symbol)
        leverage_value = int(leverage)
        if leverage_value < 1 or leverage_value > 125:
            raise ExchangeRequestError("Плечо должно быть от 1x до 125x")
        data = await self.client.signed_post(
            CHANGE_LEVERAGE,
            {"symbol": normalized, "leverage": leverage_value},
        )
        if isinstance(data, dict) and data.get("leverage") is not None:
            return int(data["leverage"])
        return leverage_value

    async def open_position(self, request: OpenPositionRequest) -> OrderResult:
        self._ensure_ready()
        normalized = normalize_symbol(request.symbol)
        previews = await self.preview_volume(
            normalized,
            request.amount_usdt,
            request.rounding,
        )
        calculation = previews["buy" if request.direction == "long" else "sell"]
        leverage = await self.set_leverage(normalized, request.leverage)
        hedge_mode = await self._hedge_mode()

        payload: dict[str, Any] = {
            "symbol": normalized,
            "side": "BUY" if request.direction == "long" else "SELL",
            "type": "MARKET",
            "quantity": plain_decimal(calculation.quantity),
            "newClientOrderId": f"arbi3_open_{int(time.time() * 1000)}",
            "newOrderRespType": "RESULT",
        }
        if hedge_mode:
            payload["positionSide"] = "LONG" if request.direction == "long" else "SHORT"

        response = await self.client.signed_post(NEW_ORDER, payload)
        order_id = str(response.get("orderId") or "") if isinstance(response, dict) else ""
        return OrderResult(
            success=True,
            message="Ордер открытия отправлен",
            order_id=order_id or None,
            raw={
                "request": payload,
                "calculation": _calculation_dict(calculation),
                "leverage": leverage,
                "response": response,
            },
        )

    async def close_position(self, request: ClosePositionRequest) -> OrderResult:
        self._ensure_ready()
        normalized = normalize_symbol(request.symbol)
        positions = await self.positions(normalized)
        target = next(
            (
                position
                for position in positions
                if position.symbol == normalized and position.direction == request.direction
            ),
            None,
        )
        if target is None:
            raise ExchangeRequestError(
                f"Не найдена открытая {request.direction} позиция по {normalized}",
            )

        quantity: float | int = target.quantity
        calculation: VolumeCalculation | None = None
        if request.amount_usdt is not None:
            previews = await self.preview_volume(
                normalized,
                request.amount_usdt,
                request.rounding,
            )
            calculation = previews["sell" if request.direction == "long" else "buy"]
            quantity = min(float(calculation.quantity), target.quantity)

        hedge_mode = await self._hedge_mode()
        payload: dict[str, Any] = {
            "symbol": normalized,
            "side": "SELL" if request.direction == "long" else "BUY",
            "type": "MARKET",
            "quantity": plain_decimal(quantity),
            "newClientOrderId": f"arbi3_close_{int(time.time() * 1000)}",
            "newOrderRespType": "RESULT",
        }
        if hedge_mode:
            payload["positionSide"] = "LONG" if request.direction == "long" else "SHORT"
        else:
            payload["reduceOnly"] = "true"

        response = await self.client.signed_post(NEW_ORDER, payload)
        order_id = str(response.get("orderId") or "") if isinstance(response, dict) else ""
        return OrderResult(
            success=True,
            message="Ордер закрытия отправлен",
            order_id=order_id or None,
            raw={
                "request": payload,
                "calculation": _calculation_dict(calculation) if calculation else None,
                "response": response,
            },
        )

    async def _hedge_mode(self) -> bool:
        data = await self.client.signed_get(POSITION_MODE)
        if not isinstance(data, dict):
            raise ExchangeRequestError("Binance не вернула режим позиций")
        value = data.get("dualSidePosition")
        if isinstance(value, str):
            return value.lower() == "true"
        return bool(value)

    async def _symbol_info(self, symbol: str) -> dict[str, Any]:
        data = await self.client.public_get(EXCHANGE_INFO)
        symbols = data.get("symbols") if isinstance(data, dict) else None
        for item in _dict_list(symbols):
            if str(item.get("symbol") or "").upper() == symbol:
                return item
        raise ExchangeRequestError(f"Binance не вернула параметры контракта {symbol}")

    def _ensure_ready(self) -> None:
        if not self.config.enabled:
            raise ExchangeDisabledError("Подключение к Binance отключено")
        if not self.config.credentials.api_key or not self.config.credentials.secret_key:
            raise ExchangeNotConfiguredError("Не указаны Binance API key и Secret key")


def _dict_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [value]
    return []


def _float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _optional_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _calculation_dict(calculation: VolumeCalculation | None) -> dict[str, Any] | None:
    if calculation is None:
        return None
    return {
        "symbol": calculation.symbol,
        "side": calculation.side,
        "requested_amount_usdt": calculation.requested_amount_usdt,
        "price": calculation.price,
        "quantity": calculation.quantity,
        "rounded_amount_usdt": calculation.rounded_amount_usdt,
        "rounding": calculation.rounding,
        "min_quantity": calculation.min_quantity,
        "max_quantity": calculation.max_quantity,
        "quantity_step": calculation.quantity_step,
        "min_notional_usdt": calculation.min_notional_usdt,
    }
