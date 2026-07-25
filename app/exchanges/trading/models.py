from dataclasses import dataclass, field
from typing import Any, Literal

ConnectionState = Literal["connected", "error", "disabled", "not_configured"]
OrderDirection = Literal["long", "short"]
NotionalRounding = Literal["down", "up"]


@dataclass(slots=True, frozen=True)
class ExchangeCredentials:
    api_key: str = ""
    secret_key: str = ""


@dataclass(slots=True, frozen=True)
class ExchangeTradingConfig:
    enabled: bool
    credentials: ExchangeCredentials = field(default_factory=ExchangeCredentials)


@dataclass(slots=True, frozen=True)
class ConnectionStatus:
    state: ConnectionState
    message: str
    position_mode: str | None = None


@dataclass(slots=True, frozen=True)
class Balance:
    currency: str
    available: float
    equity: float
    wallet_balance: float
    unrealized_pnl: float


@dataclass(slots=True, frozen=True)
class Position:
    symbol: str
    direction: OrderDirection
    quantity: float
    entry_price: float | None = None
    unrealized_pnl: float | None = None
    position_index: int | None = None


@dataclass(slots=True, frozen=True)
class VolumeCalculation:
    symbol: str
    side: Literal["buy", "sell"]
    requested_amount_usdt: float
    price: float
    quantity: float | int
    rounded_amount_usdt: float
    rounding: NotionalRounding
    min_quantity: float | None = None
    max_quantity: float | None = None
    quantity_step: float | None = None
    min_notional_usdt: float | None = None


@dataclass(slots=True, frozen=True)
class OpenPositionRequest:
    symbol: str
    direction: OrderDirection
    amount_usdt: float
    leverage: int
    rounding: NotionalRounding = "down"


@dataclass(slots=True, frozen=True)
class ClosePositionRequest:
    symbol: str
    direction: OrderDirection
    amount_usdt: float | None = None
    quantity: float | None = None
    rounding: NotionalRounding = "down"


@dataclass(slots=True, frozen=True)
class OrderResult:
    success: bool
    message: str
    order_id: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)
