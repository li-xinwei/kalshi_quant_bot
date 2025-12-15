from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

def _env(name: str, default: Optional[str] = None) -> str:
    v = os.getenv(name, default)
    if v is None:
        raise RuntimeError(f"Missing required env var: {name}")
    return v

def _env_float(name: str, default: float) -> float:
    v = os.getenv(name)
    return float(v) if v is not None else default

def _env_int(name: str, default: int) -> int:
    v = os.getenv(name)
    return int(v) if v is not None else default

@dataclass(frozen=True)
class BotConfig:
    env: str  # "demo" or "prod"
    api_key_id: str
    private_key_path: str
    host: str

    tickers: List[str]

    # Strategy config
    fair_probs: Dict[str, float]
    edge_threshold: float

    # Risk config
    max_order_count: int
    max_position_per_ticker: int

    poll_seconds: float

    @staticmethod
    def load() -> "BotConfig":
        env = os.getenv("KALSHI_ENV", "demo").lower().strip()
        if env not in ("demo", "prod"):
            raise ValueError("KALSHI_ENV must be 'demo' or 'prod'")

        api_key_id = _env("KALSHI_API_KEY_ID")
        private_key_path = _env("KALSHI_PRIVATE_KEY_PATH")

        host_demo = os.getenv("KALSHI_HOST_DEMO", "https://demo-api.kalshi.co/trade-api/v2")
        host_prod = os.getenv("KALSHI_HOST_PROD", "https://api.elections.kalshi.com/trade-api/v2")
        host = host_demo if env == "demo" else host_prod

        tickers_raw = os.getenv("TICKERS", "").strip()
        tickers = [t.strip() for t in tickers_raw.split(",") if t.strip()]
        if not tickers:
            raise RuntimeError("TICKERS is empty. Provide at least one market ticker.")

        fair_probs_json = os.getenv("FAIR_PROBS_JSON", "{}")
        try:
            fair_probs = json.loads(fair_probs_json)
        except json.JSONDecodeError as e:
            raise RuntimeError("FAIR_PROBS_JSON must be valid JSON") from e

        edge_threshold = _env_float("EDGE_THRESHOLD", 0.04)
        max_order_count = _env_int("MAX_ORDER_COUNT", 10)
        max_position_per_ticker = _env_int("MAX_POSITION_PER_TICKER", 50)
        poll_seconds = _env_float("POLL_SECONDS", 2.0)

        return BotConfig(
            env=env,
            api_key_id=api_key_id,
            private_key_path=private_key_path,
            host=host,
            tickers=tickers,
            fair_probs=fair_probs,
            edge_threshold=edge_threshold,
            max_order_count=max_order_count,
            max_position_per_ticker=max_position_per_ticker,
            poll_seconds=poll_seconds,
        )
