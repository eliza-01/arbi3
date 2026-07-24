from datetime import UTC, datetime
from decimal import Decimal

import httpx

from app.exchanges.contracts import ExchangeQuote, InstrumentDescriptor


class BybitRestClient:
    base_url = "https://api.bybit.com"

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=20.0)

    async def close(self) -> None:
        await self._client.aclose()

    async def fetch_instruments(self) -> list[InstrumentDescriptor]:
        cursor = ""
        result: list[InstrumentDescriptor] = []
        while True:
            params = {"category": "linear", "limit": 1000}
            if cursor:
                params["cursor"] = cursor
            response = await self._client.get("/v5/market/instruments-info", params=params)
            response.raise_for_status()
            payload = response.json()
            if payload.get("retCode") != 0:
                raise RuntimeError(f"Bybit instruments error: {payload.get('retMsg')}")
            page = payload["result"]
            for item in page.get("list", []):
                if item.get("status") != "Trading":
                    continue
                if item.get("contractType") != "LinearPerpetual":
                    continue
                if item.get("quoteCoin") != "USDT" or item.get("settleCoin") != "USDT":
                    continue
                result.append(
                    InstrumentDescriptor(
                        symbol=item["symbol"],
                        base_asset=item["baseCoin"],
                        quote_asset=item["quoteCoin"],
                        contract_type="PERPETUAL",
                        metadata={"settle_coin": item.get("settleCoin")},
                    )
                )
            cursor = page.get("nextPageCursor") or ""
            if not cursor:
                break
        return result

    async def poll_quotes(self, symbols: set[str]) -> list[ExchangeQuote]:
        response = await self._client.get("/v5/market/tickers", params={"category": "linear"})
        response.raise_for_status()
        payload = response.json()
        if payload.get("retCode") != 0:
            raise RuntimeError(f"Bybit tickers error: {payload.get('retMsg')}")
        now = datetime.now(UTC)
        result: list[ExchangeQuote] = []
        for item in payload["result"].get("list", []):
            symbol = item.get("symbol")
            if symbol not in symbols:
                continue
            bid = Decimal(item["bid1Price"])
            ask = Decimal(item["ask1Price"])
            last = Decimal(item.get("lastPrice") or ((bid + ask) / Decimal(2)))
            result.append(
                ExchangeQuote(
                    exchange_code="bybit",
                    symbol=symbol,
                    bid=bid,
                    ask=ask,
                    last=last,
                    observed_at=now,
                )
            )
        return result
