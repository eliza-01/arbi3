from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.services.instruments.contracts import CatalogAsset
from app.services.quotes.store import StoredQuote


@dataclass(slots=True, frozen=True)
class SpreadResult:
    asset_id: int
    buy_exchange: str
    sell_exchange: str
    buy_exchange_id: int
    sell_exchange_id: int
    buy_price: Decimal
    sell_price: Decimal
    delta_abs: Decimal
    delta_pct: Decimal
    observed_at: datetime


def calculate_directional_spreads(
    asset: CatalogAsset, quotes: dict[str, StoredQuote]
) -> list[SpreadResult]:
    results: list[SpreadResult] = []
    exchange_codes = sorted(quotes)
    for buy_code in exchange_codes:
        for sell_code in exchange_codes:
            if buy_code == sell_code:
                continue
            buy_quote = quotes[buy_code]
            sell_quote = quotes[sell_code]
            if buy_quote.ask <= 0:
                continue
            delta_abs = sell_quote.bid - buy_quote.ask
            delta_pct = (delta_abs / buy_quote.ask) * Decimal(100)
            results.append(
                SpreadResult(
                    asset_id=asset.id,
                    buy_exchange=buy_code,
                    sell_exchange=sell_code,
                    buy_exchange_id=asset.exchange_ids[buy_code],
                    sell_exchange_id=asset.exchange_ids[sell_code],
                    buy_price=buy_quote.ask,
                    sell_price=sell_quote.bid,
                    delta_abs=delta_abs,
                    delta_pct=delta_pct,
                    observed_at=max(buy_quote.observed_at, sell_quote.observed_at),
                )
            )
    return results
