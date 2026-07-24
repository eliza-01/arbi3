import asyncio
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal

import websockets

from app.exchanges.contracts import ExchangeQuote


class BybitWebSocketClient:
    url = "wss://stream.bybit.com/v5/public/linear"

    async def stream_quotes(self, symbols: set[str]) -> AsyncIterator[ExchangeQuote]:
        if not symbols:
            return
        topics = [f"tickers.{symbol}" for symbol in sorted(symbols)]
        state: dict[str, dict[str, str]] = {}
        async with websockets.connect(
            self.url,
            ping_interval=None,
            close_timeout=5,
            max_queue=4096,
        ) as socket:
            for start in range(0, len(topics), 200):
                await socket.send(
                    json.dumps({"op": "subscribe", "args": topics[start : start + 200]})
                )

            async def heartbeat() -> None:
                while True:
                    await asyncio.sleep(20)
                    await socket.send(json.dumps({"op": "ping"}))

            heartbeat_task = asyncio.create_task(heartbeat())
            try:
                while True:
                    raw = await asyncio.wait_for(socket.recv(), timeout=60)
                    message = json.loads(raw)
                    topic = message.get("topic", "")
                    if not topic.startswith("tickers."):
                        continue
                    data = message.get("data") or {}
                    if isinstance(data, list):
                        data = data[0] if data else {}
                    symbol = data.get("symbol") or topic.split(".", 1)[1]
                    merged = state.setdefault(symbol, {})
                    merged.update({key: value for key, value in data.items() if value not in (None, "")})
                    bid_raw = merged.get("bid1Price")
                    ask_raw = merged.get("ask1Price")
                    if not bid_raw or not ask_raw:
                        continue
                    bid = Decimal(bid_raw)
                    ask = Decimal(ask_raw)
                    last = Decimal(merged.get("lastPrice") or ((bid + ask) / Decimal(2)))
                    timestamp_ms = message.get("ts")
                    observed_at = (
                        datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)
                        if timestamp_ms
                        else datetime.now(UTC)
                    )
                    yield ExchangeQuote(
                        exchange_code="bybit",
                        symbol=symbol,
                        bid=bid,
                        ask=ask,
                        last=last,
                        observed_at=observed_at,
                    )
            finally:
                heartbeat_task.cancel()
                await asyncio.gather(heartbeat_task, return_exceptions=True)
