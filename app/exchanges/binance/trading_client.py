import time
from typing import Any

import httpx

from app.exchanges.binance.trading_constants import API_BASE_URL, SERVER_TIME
from app.exchanges.binance.trading_signer import build_headers, signed_params
from app.exchanges.trading.errors import ExchangeRequestError


class BinanceApiError(ExchangeRequestError):
    def __init__(self, message: str, code: int | None = None) -> None:
        super().__init__(message)
        self.code = code


class BinanceFuturesTradingClient:
    def __init__(
        self,
        api_key: str,
        secret_key: str,
        base_url: str = API_BASE_URL,
        timeout: float = 20.0,
    ) -> None:
        self.api_key = api_key.strip()
        self.secret_key = secret_key.strip()
        self._client = httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=timeout)
        self._time_offset_ms = 0
        self._time_synced = False

    async def close(self) -> None:
        await self._client.aclose()

    async def public_get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        return await self._request("GET", endpoint, params=params, signed=False)

    async def signed_get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        return await self._request("GET", endpoint, params=params, signed=True)

    async def signed_post(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        return await self._request("POST", endpoint, params=params, signed=True)

    async def sync_server_time(self) -> None:
        started_ms = _now_ms()
        data = await self.public_get(SERVER_TIME)
        finished_ms = _now_ms()
        if not isinstance(data, dict) or data.get("serverTime") is None:
            raise BinanceApiError(f"Binance не вернула serverTime: {data!r}")
        try:
            server_time_ms = int(data["serverTime"])
        except (TypeError, ValueError) as exc:
            raise BinanceApiError(f"Binance вернула некорректный serverTime: {data!r}") from exc
        self._time_offset_ms = server_time_ms - ((started_ms + finished_ms) // 2)
        self._time_synced = True

    def _timestamp_ms(self) -> int:
        return _now_ms() + self._time_offset_ms

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None,
        signed: bool,
        retry_on_timestamp_error: bool = True,
    ) -> Any:
        if signed and (not self.api_key or not self.secret_key):
            raise BinanceApiError("Не указаны Binance API key и Secret key")
        if signed and not self._time_synced:
            await self.sync_server_time()

        request_params = (
            signed_params(self.secret_key, params, timestamp_ms=self._timestamp_ms())
            if signed
            else dict(params or {})
        )
        try:
            response = await self._client.request(
                method,
                endpoint,
                params=request_params,
                headers=build_headers(self.api_key if signed else ""),
            )
            data = _response_json(response)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            data = _response_json(exc.response)
            code, message = _api_error(data)
            if signed and retry_on_timestamp_error and code == -1021:
                await self.sync_server_time()
                return await self._request(
                    method,
                    endpoint,
                    params=params,
                    signed=signed,
                    retry_on_timestamp_error=False,
                )
            body = exc.response.text[:1000]
            raise BinanceApiError(
                f"Binance HTTP {exc.response.status_code}: {message or body}",
                code,
            ) from exc
        except httpx.HTTPError as exc:
            raise BinanceApiError(f"Binance request failed: {exc}") from exc

        code, message = _api_error(data)
        if code is not None and code < 0:
            raise BinanceApiError(f"Binance API {code}: {message or data}", code)
        return data


def _now_ms() -> int:
    return int(time.time() * 1000)


def _response_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None


def _api_error(data: Any) -> tuple[int | None, str | None]:
    if not isinstance(data, dict):
        return None, None
    try:
        code = int(data["code"]) if data.get("code") is not None else None
    except (TypeError, ValueError):
        code = None
    message = data.get("msg") or data.get("message")
    return code, str(message) if message is not None else None
