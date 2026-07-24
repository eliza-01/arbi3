from collections.abc import AsyncIterator

from app.exchanges.binance.rest import BinanceRestClient
from app.exchanges.binance.websocket import BinanceWebSocketClient
from app.exchanges.contracts import ExchangeQuote, InstrumentDescriptor


class BinanceAdapter:
    code = "binance"
    name = "Binance"

    def __init__(self) -> None:
        self._rest = BinanceRestClient()
        self._websocket = BinanceWebSocketClient()

    async def close(self) -> None:
        await self._rest.close()

    async def fetch_instruments(self) -> list[InstrumentDescriptor]:
        return await self._rest.fetch_instruments()

    def stream_quotes(self, symbols: set[str]) -> AsyncIterator[ExchangeQuote]:
        return self._websocket.stream_quotes(symbols)

    async def poll_quotes(self, symbols: set[str]) -> list[ExchangeQuote]:
        return await self._rest.poll_quotes(symbols)
