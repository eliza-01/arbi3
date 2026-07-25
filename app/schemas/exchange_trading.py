from typing import Literal

from pydantic import BaseModel, Field


class ExchangeConnectRequest(BaseModel):
    api_key: str | None = None
    secret_key: str | None = None


class BinanceConnectRequest(ExchangeConnectRequest):
    pass


class BybitConnectRequest(ExchangeConnectRequest):
    pass


class ExchangeLeverageRequest(BaseModel):
    symbol: str = Field(min_length=1)
    leverage: int = Field(ge=1, le=125)


class BinanceLeverageRequest(ExchangeLeverageRequest):
    pass


class BybitLeverageRequest(ExchangeLeverageRequest):
    pass


class ExchangeOpenPositionRequest(BaseModel):
    symbol: str = Field(min_length=1)
    direction: Literal["long", "short"]
    amount_usdt: float | None = Field(default=None, gt=0)
    leverage: int | None = Field(default=None, ge=1, le=125)
    rounding: Literal["down", "up"] | None = None
    confirm: bool = False


class BinanceOpenPositionRequest(ExchangeOpenPositionRequest):
    pass


class BybitOpenPositionRequest(ExchangeOpenPositionRequest):
    pass


class ExchangeClosePositionRequest(BaseModel):
    symbol: str = Field(min_length=1)
    direction: Literal["long", "short"]
    amount_usdt: float | None = Field(default=None, gt=0)
    rounding: Literal["down", "up"] | None = None
    confirm: bool = False


class BinanceClosePositionRequest(ExchangeClosePositionRequest):
    pass


class BybitClosePositionRequest(ExchangeClosePositionRequest):
    pass


class TradingSettingsUpdateRequest(BaseModel):
    position_usdt: float = Field(gt=0)
    leverage: int = Field(ge=1, le=125)
    rounding: Literal["down", "up"]
