from collections.abc import AsyncIterator

from app.exchanges.bybit.rest import BybitRestClient
from app.exchanges.bybit.websocket import BybitWebSocketClient
from app.exchanges.contracts import ExchangeQuote, InstrumentDescriptor


class BybitAdapter:
    code = "bybit"
    name = "Bybit"

    def __init__(self) -> None:
        self._rest = BybitRestClient()
        self._websocket = BybitWebSocketClient()

    async def close(self) -> None:
        await self._rest.close()

    async def fetch_instruments(self) -> list[InstrumentDescriptor]:
        return await self._rest.fetch_instruments()

    def stream_quotes(self, symbols: set[str]) -> AsyncIterator[ExchangeQuote]:
        return self._websocket.stream_quotes(symbols)

    async def poll_quotes(self, symbols: set[str]) -> list[ExchangeQuote]:
        return await self._rest.poll_quotes(symbols)
