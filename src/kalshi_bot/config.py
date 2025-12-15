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


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return bool(default)
    return v.strip().lower() in ("1", "true", "yes", "y", "on")

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

    # Fees / execution assumptions (used for EV calc)
    fee_kind: str  # "taker" | "maker" | "none"
    taker_fee_rate: float
    maker_fee_rate: float
    min_net_ev_per_contract: float  # USD
    post_only: bool

    # Optional: in-play fair-prob model (Kalshi milestones + live_data)
    use_live_data: bool
    coef_score_diff: float
    coef_time_left_min: float
    coef_prior: float

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

        fee_kind = os.getenv("FEE_KIND", "taker").strip().lower()
        if fee_kind not in ("taker", "maker", "none"):
            raise ValueError("FEE_KIND must be one of: taker, maker, none")

        taker_fee_rate = _env_float("TAKER_FEE_RATE", 0.07)
        maker_fee_rate = _env_float("MAKER_FEE_RATE", 0.0175)
        min_net_ev_per_contract = _env_float("MIN_NET_EV_PER_CONTRACT", 0.0)
        post_only = _env_bool("POST_ONLY", True)

        use_live_data = _env_bool("USE_LIVE_DATA", False)
        coef_score_diff = _env_float("COEF_SCORE_DIFF", 0.12)
        coef_time_left_min = _env_float("COEF_TIME_LEFT_MIN", -0.03)
        coef_prior = _env_float("COEF_PRIOR", 1.0)
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
            fee_kind=fee_kind,
            taker_fee_rate=taker_fee_rate,
            maker_fee_rate=maker_fee_rate,
            min_net_ev_per_contract=min_net_ev_per_contract,
            post_only=post_only,
            use_live_data=use_live_data,
            coef_score_diff=coef_score_diff,
            coef_time_left_min=coef_time_left_min,
            coef_prior=coef_prior,
            max_order_count=max_order_count,
            max_position_per_ticker=max_position_per_ticker,
            poll_seconds=poll_seconds,
        )
