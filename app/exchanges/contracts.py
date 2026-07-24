from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Protocol


@dataclass(slots=True, frozen=True)
class InstrumentDescriptor:
    symbol: str
    base_asset: str
    quote_asset: str
    contract_type: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ExchangeQuote:
    exchange_code: str
    symbol: str
    bid: Decimal
    ask: Decimal
    last: Decimal
    observed_at: datetime


class ExchangeAdapter(Protocol):
    code: str
    name: str

    async def fetch_instruments(self) -> list[InstrumentDescriptor]: ...

    def stream_quotes(self, symbols: set[str]) -> AsyncIterator[ExchangeQuote]: ...

    async def poll_quotes(self, symbols: set[str]) -> list[ExchangeQuote]: ...
