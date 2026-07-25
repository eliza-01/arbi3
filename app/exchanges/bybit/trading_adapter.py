import time
from typing import Any

from app.exchanges.binance.volume import normalize_symbol, plain_decimal
from app.exchanges.bybit.trading_client import BybitApiError, BybitFuturesTradingClient
from app.exchanges.bybit.trading_constants import (
    CREATE_ORDER,
    INSTRUMENTS_INFO,
    POSITION_LIST,
    SERVER_TIME,
    SET_LEVERAGE,
    TICKERS,
    WALLET_BALANCE,
)
from app.exchanges.bybit.volume import calculate_volume, ticker_price
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


class BybitTradingAdapter:
    code = "bybit"
    name = "Bybit USDT Perpetual"

    def __init__(
        self,
        config: ExchangeTradingConfig,
        client: BybitFuturesTradingClient | None = None,
    ) -> None:
        self.config = config
        self.client = client or BybitFuturesTradingClient(
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
            await self.client.public_get(SERVER_TIME)
            await self.client.signed_get(
                WALLET_BALANCE,
                {"accountType": "UNIFIED", "coin": "USDT"},
            )
            return ConnectionStatus("connected", "Подключено · Unified Account")
        except Exception as exc:
            return ConnectionStatus("error", str(exc))

    async def balance(self, currency: str = "USDT") -> Balance:
        self._ensure_ready()
        payload = await self.client.signed_get(
            WALLET_BALANCE,
            {"accountType": "UNIFIED", "coin": currency.upper()},
        )
        result = _result(payload)
        accounts = _dict_list(result.get("list"))
        if not accounts:
            return _empty_balance(currency)
        account = accounts[0]
        coin = next(
            (
                item
                for item in _dict_list(account.get("coin"))
                if str(item.get("coin") or "").upper() == currency.upper()
            ),
            {},
        )
        return Balance(
            currency=currency.upper(),
            available=_float(account.get("totalAvailableBalance")),
            equity=_float(account.get("totalEquity")),
            wallet_balance=_float(coin.get("walletBalance") or account.get("totalWalletBalance")),
            unrealized_pnl=_float(coin.get("unrealisedPnl") or account.get("totalPerpUPL")),
        )

    async def positions(self, symbol: str | None = None) -> list[Position]:
        self._ensure_ready()
        params: dict[str, Any] = {"category": "linear"}
        if symbol:
            params["symbol"] = normalize_symbol(symbol)
        else:
            params["settleCoin"] = "USDT"
            params["limit"] = 200
        payload = await self.client.signed_get(POSITION_LIST, params)
        rows = _dict_list(_result(payload).get("list"))
        positions: list[Position] = []
        for item in rows:
            quantity = _float(item.get("size"))
            side = str(item.get("side") or "")
            if quantity <= 0 or side not in {"Buy", "Sell"}:
                continue
            positions.append(
                Position(
                    symbol=str(item.get("symbol") or ""),
                    direction="long" if side == "Buy" else "short",
                    quantity=quantity,
                    entry_price=_optional_float(item.get("avgPrice")),
                    unrealized_pnl=_optional_float(item.get("unrealisedPnl")),
                    position_index=_int(item.get("positionIdx"), 0),
                ),
            )
        return positions

    async def preview_volume(
        self,
        symbol: str,
        amount_usdt: float,
        rounding: str,
    ) -> dict[str, VolumeCalculation]:
        normalized = normalize_symbol(symbol)
        contract = await self._symbol_info(normalized)
        ticker_payload = await self.client.public_get(
            TICKERS,
            {"category": "linear", "symbol": normalized},
        )
        tickers = _dict_list(_result(ticker_payload).get("list"))
        if not tickers:
            raise ExchangeRequestError(f"Bybit не вернула котировку {normalized}")
        ticker = tickers[0]
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
        contract = await self._symbol_info(normalized)
        leverage_filter = contract.get("leverageFilter") if isinstance(contract.get("leverageFilter"), dict) else {}
        maximum = _float(leverage_filter.get("maxLeverage")) or 125
        leverage_value = int(leverage)
        if leverage_value < 1 or leverage_value > maximum:
            raise ExchangeRequestError(
                f"Плечо для {normalized} должно быть от 1x до {int(maximum)}x",
            )
        try:
            await self.client.signed_post(
                SET_LEVERAGE,
                {
                    "category": "linear",
                    "symbol": normalized,
                    "buyLeverage": str(leverage_value),
                    "sellLeverage": str(leverage_value),
                },
            )
        except BybitApiError as exc:
            if exc.code != 110043:
                raise
        return leverage_value

    async def open_position(self, request: OpenPositionRequest) -> OrderResult:
        self._ensure_ready()
        normalized = normalize_symbol(request.symbol)
        previews = await self.preview_volume(normalized, request.amount_usdt, request.rounding)
        calculation = previews["buy" if request.direction == "long" else "sell"]
        leverage = await self.set_leverage(normalized, request.leverage)
        position_index = await self._position_index(normalized, request.direction)
        body: dict[str, Any] = {
            "category": "linear",
            "symbol": normalized,
            "side": "Buy" if request.direction == "long" else "Sell",
            "orderType": "Market",
            "qty": plain_decimal(calculation.quantity),
            "positionIdx": position_index,
            "reduceOnly": False,
            "closeOnTrigger": False,
            "orderLinkId": f"arbi3-open-{int(time.time() * 1000)}",
        }
        response = await self.client.signed_post(CREATE_ORDER, body)
        result = _result(response)
        return OrderResult(
            success=True,
            message="Ордер открытия отправлен",
            order_id=str(result.get("orderId") or "") or None,
            raw={
                "request": body,
                "calculation": _calculation_dict(calculation),
                "leverage": leverage,
                "response": response,
            },
        )

    async def close_position(self, request: ClosePositionRequest) -> OrderResult:
        self._ensure_ready()
        normalized = normalize_symbol(request.symbol)
        target = next(
            (
                position
                for position in await self.positions(normalized)
                if position.direction == request.direction
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
            previews = await self.preview_volume(normalized, request.amount_usdt, request.rounding)
            calculation = previews["sell" if request.direction == "long" else "buy"]
            quantity = min(float(calculation.quantity), target.quantity)

        body: dict[str, Any] = {
            "category": "linear",
            "symbol": normalized,
            "side": "Sell" if request.direction == "long" else "Buy",
            "orderType": "Market",
            "qty": plain_decimal(quantity),
            "positionIdx": target.position_index or 0,
            "reduceOnly": True,
            "closeOnTrigger": False,
            "orderLinkId": f"arbi3-close-{int(time.time() * 1000)}",
        }
        response = await self.client.signed_post(CREATE_ORDER, body)
        result = _result(response)
        return OrderResult(
            success=True,
            message="Ордер закрытия отправлен",
            order_id=str(result.get("orderId") or "") or None,
            raw={
                "request": body,
                "calculation": _calculation_dict(calculation) if calculation else None,
                "response": response,
            },
        )

    async def _position_index(self, symbol: str, direction: str) -> int:
        payload = await self.client.signed_get(
            POSITION_LIST,
            {"category": "linear", "symbol": symbol},
        )
        indices = {
            _int(item.get("positionIdx"), 0)
            for item in _dict_list(_result(payload).get("list"))
        }
        if 1 in indices or 2 in indices:
            return 1 if direction == "long" else 2
        return 0

    async def _symbol_info(self, symbol: str) -> dict[str, Any]:
        payload = await self.client.public_get(
            INSTRUMENTS_INFO,
            {"category": "linear", "symbol": symbol},
        )
        items = _dict_list(_result(payload).get("list"))
        if not items:
            raise ExchangeRequestError(f"Bybit не нашла USDT perpetual {symbol}")
        item = items[0]
        if item.get("contractType") != "LinearPerpetual" or item.get("status") != "Trading":
            raise ExchangeRequestError(f"Bybit-контракт {symbol} недоступен для торговли")
        return item

    def _ensure_ready(self) -> None:
        if not self.config.enabled:
            raise ExchangeDisabledError("Подключение Bybit отключено")
        if not self.config.credentials.api_key or not self.config.credentials.secret_key:
            raise ExchangeNotConfiguredError("Bybit API key и Secret key не настроены")


def _result(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict) and isinstance(payload.get("result"), dict):
        return payload["result"]
    return {}


def _dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _optional_float(value: Any) -> float | None:
    try:
        return float(value) if value not in {None, ""} else None
    except (TypeError, ValueError):
        return None


def _int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _empty_balance(currency: str) -> Balance:
    return Balance(currency.upper(), 0.0, 0.0, 0.0, 0.0)


def _calculation_dict(value: VolumeCalculation | None) -> dict[str, Any] | None:
    if value is None:
        return None
    return {
        "side": value.side,
        "price": value.price,
        "quantity": value.quantity,
        "rounded_amount_usdt": value.rounded_amount_usdt,
        "rounding": value.rounding,
    }
