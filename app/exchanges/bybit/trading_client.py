import json
import time
from typing import Any

import httpx

from app.exchanges.bybit.trading_constants import API_BASE_URL, RECV_WINDOW, SERVER_TIME
from app.exchanges.bybit.trading_signer import json_body, query_string, signed_headers
from app.exchanges.trading.errors import ExchangeRequestError


class BybitApiError(ExchangeRequestError):
    def __init__(self, message: str, code: int | None = None) -> None:
        super().__init__(message)
        self.code = code


class BybitFuturesTradingClient:
    def __init__(
        self,
        api_key: str,
        secret_key: str,
        base_url: str = API_BASE_URL,
        timeout: float = 20.0,
    ) -> None:
        self.api_key = api_key.strip()
        self.secret_key = secret_key.strip()
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._time_offset_ms = 0
        self._time_synced = False
        self._client = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        await self._client.aclose()

    async def public_get(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        return await self._request("GET", endpoint, params=params, signed=False)

    async def signed_get(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        return await self._request("GET", endpoint, params=params, signed=True)

    async def signed_post(self, endpoint: str, payload: dict[str, Any] | None = None) -> Any:
        return await self._request("POST", endpoint, payload=payload, signed=True)

    async def sync_server_time(self) -> None:
        started_ms = _now_ms()
        payload = await self.public_get(SERVER_TIME)
        finished_ms = _now_ms()
        server_time = payload.get("time") if isinstance(payload, dict) else None
        if server_time is None:
            raise BybitApiError("Bybit не вернула серверное время")
        local_midpoint_ms = (started_ms + finished_ms) // 2
        self._time_offset_ms = int(server_time) - local_midpoint_ms
        self._time_synced = True

    def _timestamp_ms(self) -> int:
        return _now_ms() + self._time_offset_ms

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
        signed: bool,
        retry_on_timestamp_error: bool = True,
    ) -> Any:
        if signed and (not self.api_key or not self.secret_key):
            raise BybitApiError("Не указаны Bybit API key и/или Secret key")
        if signed and not self._time_synced:
            await self.sync_server_time()

        query = query_string(params)
        body = json_body(payload)
        payload_text = query if method == "GET" else body
        url = f"{self.base_url}{endpoint}"
        if query:
            url = f"{url}?{query}"

        headers = {"Accept": "application/json"}
        if signed:
            headers = signed_headers(
                api_key=self.api_key,
                secret_key=self.secret_key,
                timestamp_ms=self._timestamp_ms(),
                recv_window=RECV_WINDOW,
                payload_text=payload_text,
            )

        try:
            response = await self._client.request(
                method,
                url,
                headers=headers,
                content=body if method == "POST" else None,
            )
            data = response.json()
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            message = _http_message(exc.response)
            raise BybitApiError(
                f"Bybit HTTP {exc.response.status_code}: {message}",
            ) from exc
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            raise BybitApiError(f"Bybit request failed: {exc}") from exc

        code = _int(data.get("retCode")) if isinstance(data, dict) else None
        message = str(data.get("retMsg") or "") if isinstance(data, dict) else ""
        if code not in {None, 0}:
            if retry_on_timestamp_error and code == 10002:
                await self.sync_server_time()
                return await self._request(
                    method,
                    endpoint,
                    params=params,
                    payload=payload,
                    signed=signed,
                    retry_on_timestamp_error=False,
                )
            raise BybitApiError(f"Bybit API {code}: {message or data}", code)
        return data


def _now_ms() -> int:
    return int(time.time() * 1000)


def _int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _http_message(response: httpx.Response) -> str:
    try:
        data = response.json()
    except json.JSONDecodeError:
        return response.text[:1000]
    if isinstance(data, dict):
        return str(data.get("retMsg") or data.get("message") or data)
    return str(data)
