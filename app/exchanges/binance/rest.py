from datetime import UTC, datetime
from decimal import Decimal

import httpx

from app.exchanges.contracts import ExchangeQuote, InstrumentDescriptor


class BinanceRestClient:
    base_url = "https://fapi.binance.com"

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=20.0)

    async def close(self) -> None:
        await self._client.aclose()

    async def fetch_instruments(self) -> list[InstrumentDescriptor]:
        response = await self._client.get("/fapi/v1/exchangeInfo")
        response.raise_for_status()
        result: list[InstrumentDescriptor] = []
        for item in response.json().get("symbols", []):
            if item.get("status") != "TRADING":
                continue
            if item.get("contractType") != "PERPETUAL":
                continue
            if item.get("quoteAsset") != "USDT":
                continue
            result.append(
                InstrumentDescriptor(
                    symbol=item["symbol"],
                    base_asset=item["baseAsset"],
                    quote_asset=item["quoteAsset"],
                    contract_type="PERPETUAL",
                    metadata={"margin_asset": item.get("marginAsset")},
                )
            )
        return result

    async def poll_quotes(self, symbols: set[str]) -> list[ExchangeQuote]:
        response = await self._client.get("/fapi/v1/ticker/bookTicker")
        response.raise_for_status()
        now = datetime.now(UTC)
        result: list[ExchangeQuote] = []
        for item in response.json():
            symbol = item.get("symbol")
            if symbol not in symbols:
                continue
            bid = Decimal(item["bidPrice"])
            ask = Decimal(item["askPrice"])
            result.append(
                ExchangeQuote(
                    exchange_code="binance",
                    symbol=symbol,
                    bid=bid,
                    ask=ask,
                    last=(bid + ask) / Decimal(2),
                    observed_at=now,
                )
            )
        return result
