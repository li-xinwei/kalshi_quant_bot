from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

from .auth import KalshiSigner, HttpMethod


class KalshiHTTPError(RuntimeError):
    pass


@dataclass
class RateLimiter:
    """
    Simple token-bucket rate limiter. Kalshi publishes per-second read/write limits by tier.
    For a starter bot, this is usually enough.
    """
    per_second: float
    _tokens: float = 0.0
    _last: float = 0.0

    def __post_init__(self):
        self._tokens = self.per_second
        self._last = time.monotonic()

    def acquire(self, tokens: float = 1.0) -> None:
        while True:
            now = time.monotonic()
            elapsed = now - self._last
            self._last = now
            self._tokens = min(self.per_second, self._tokens + elapsed * self.per_second)

            if self._tokens >= tokens:
                self._tokens -= tokens
                return

            time.sleep(max(0.01, (tokens - self._tokens) / self.per_second))


@dataclass
class KalshiHTTPClient:
    host: str  # e.g. https://demo-api.kalshi.co/trade-api/v2
    signer: Optional[KalshiSigner] = None
    read_rl: Optional[RateLimiter] = None
    write_rl: Optional[RateLimiter] = None
    timeout_s: float = 10.0

    def _headers(self, method: HttpMethod, path: str) -> Dict[str, str]:
        if self.signer is None:
            return {}

        ts_ms = int(time.time() * 1000)
        sig = self.signer.sign(ts_ms, method, path)
        return {
            "KALSHI-ACCESS-KEY": self.signer.api_key_id,
            "KALSHI-ACCESS-TIMESTAMP": str(ts_ms),
            "KALSHI-ACCESS-SIGNATURE": sig,
        }

    def request(
        self,
        method: HttpMethod,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        is_write: bool = False,
    ) -> Dict[str, Any]:
        if is_write and self.write_rl:
            self.write_rl.acquire()
        if (not is_write) and self.read_rl:
            self.read_rl.acquire()

        # IMPORTANT: signature uses path WITHOUT query params.
        url = f"{self.host}{path}"
        headers = {"Content-Type": "application/json", **self._headers(method, path)}

        resp = requests.request(
            method=method,
            url=url,
            params=params,
            json=json_body,
            headers=headers,
            timeout=self.timeout_s,
        )
        if not resp.ok:
            raise KalshiHTTPError(f"{method} {path} failed: {resp.status_code} {resp.text}")

        try:
            return resp.json()
        except Exception as e:
            raise KalshiHTTPError(f"Non-JSON response: {resp.text[:200]}") from e

    # Convenience helpers
    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self.request("GET", path, params=params, is_write=False)

    def post(self, path: str, json_body: Dict[str, Any]) -> Dict[str, Any]:
        return self.request("POST", path, json_body=json_body, is_write=True)

    def delete(self, path: str) -> Dict[str, Any]:
        return self.request("DELETE", path, is_write=True)
