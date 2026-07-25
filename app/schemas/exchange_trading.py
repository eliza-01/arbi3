from typing import Literal

from pydantic import BaseModel, Field


class BinanceConnectRequest(BaseModel):
    api_key: str | None = None
    secret_key: str | None = None


class BinanceLeverageRequest(BaseModel):
    symbol: str = Field(min_length=1)
    leverage: int = Field(ge=1, le=125)


class BinanceOpenPositionRequest(BaseModel):
    symbol: str = Field(min_length=1)
    direction: Literal["long", "short"]
    amount_usdt: float | None = Field(default=None, gt=0)
    leverage: int | None = Field(default=None, ge=1, le=125)
    rounding: Literal["down", "up"] | None = None
    confirm: bool = False


class BinanceClosePositionRequest(BaseModel):
    symbol: str = Field(min_length=1)
    direction: Literal["long", "short"]
    amount_usdt: float | None = Field(default=None, gt=0)
    rounding: Literal["down", "up"] | None = None
    confirm: bool = False


class TradingSettingsUpdateRequest(BaseModel):
    position_usdt: float = Field(gt=0)
    leverage: int = Field(ge=1, le=125)
    rounding: Literal["down", "up"]
