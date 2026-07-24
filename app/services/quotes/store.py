import asyncio
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.exchanges.contracts import ExchangeQuote


@dataclass(slots=True, frozen=True)
class StoredQuote:
    bid: Decimal
    ask: Decimal
    last: Decimal
    observed_at: datetime


class QuoteStore:
    def __init__(self) -> None:
        self._quotes: dict[int, dict[str, StoredQuote]] = {}
        self._lock = asyncio.Lock()

    async def put(self, asset_id: int, quote: ExchangeQuote) -> None:
        async with self._lock:
            self._quotes.setdefault(asset_id, {})[quote.exchange_code] = StoredQuote(
                bid=quote.bid,
                ask=quote.ask,
                last=quote.last,
                observed_at=quote.observed_at,
            )

    async def snapshot(self) -> dict[int, dict[str, StoredQuote]]:
        async with self._lock:
            return {asset_id: dict(exchange_quotes) for asset_id, exchange_quotes in self._quotes.items()}

    async def clear_except(self, asset_ids: set[int]) -> None:
        async with self._lock:
            self._quotes = {
                asset_id: quotes
                for asset_id, quotes in self._quotes.items()
                if asset_id in asset_ids
            }
