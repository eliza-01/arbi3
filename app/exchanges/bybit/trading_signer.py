import hashlib
import hmac
import json
from typing import Any
from urllib.parse import urlencode


def query_string(params: dict[str, Any] | None = None) -> str:
    return urlencode(dict(params or {}), doseq=True)


def json_body(payload: dict[str, Any] | None = None) -> str:
    return json.dumps(dict(payload or {}), ensure_ascii=False, separators=(",", ":"))


def signature(
    secret_key: str,
    timestamp_ms: int,
    api_key: str,
    recv_window: int,
    payload_text: str,
) -> str:
    source = f"{timestamp_ms}{api_key}{recv_window}{payload_text}"
    return hmac.new(
        secret_key.encode("utf-8"),
        source.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def signed_headers(
    *,
    api_key: str,
    secret_key: str,
    timestamp_ms: int,
    recv_window: int,
    payload_text: str,
) -> dict[str, str]:
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-BAPI-API-KEY": api_key,
        "X-BAPI-TIMESTAMP": str(timestamp_ms),
        "X-BAPI-RECV-WINDOW": str(recv_window),
        "X-BAPI-SIGN-TYPE": "2",
        "X-BAPI-SIGN": signature(
            secret_key,
            timestamp_ms,
            api_key,
            recv_window,
            payload_text,
        ),
    }
