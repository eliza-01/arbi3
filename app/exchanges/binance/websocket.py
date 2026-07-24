import asyncio
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal

import websockets

from app.exchanges.contracts import ExchangeQuote


class BinanceWebSocketClient:
    url = "wss://fstream.binance.com/public/stream"

    async def stream_quotes(self, symbols: set[str]) -> AsyncIterator[ExchangeQuote]:
        if not symbols:
            return
        params = [f"{symbol.lower()}@bookTicker" for symbol in sorted(symbols)]
        async with websockets.connect(
            self.url,
            ping_interval=20,
            ping_timeout=20,
            close_timeout=5,
            max_queue=4096,
        ) as socket:
            for request_id, start in enumerate(range(0, len(params), 200), start=1):
                await socket.send(
                    json.dumps(
                        {
                            "method": "SUBSCRIBE",
                            "params": params[start : start + 200],
                            "id": request_id,
                        }
                    )
                )
            while True:
                raw = await asyncio.wait_for(socket.recv(), timeout=90)
                message = json.loads(raw)
                data = message.get("data", message)
                if data.get("e") != "bookTicker":
                    continue
                if data.get("st") not in (None, 1):
                    continue
                bid = Decimal(data["b"])
                ask = Decimal(data["a"])
                event_ms = data.get("E") or data.get("T")
                observed_at = (
                    datetime.fromtimestamp(event_ms / 1000, tz=UTC)
                    if event_ms
                    else datetime.now(UTC)
                )
                yield ExchangeQuote(
                    exchange_code="binance",
                    symbol=data["s"],
                    bid=bid,
                    ask=ask,
                    last=(bid + ask) / Decimal(2),
                    observed_at=observed_at,
                )
