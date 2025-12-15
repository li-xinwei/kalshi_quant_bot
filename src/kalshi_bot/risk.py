from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from .models import OrderIntent
from .kalshi.api import KalshiAPI


@dataclass
class RiskLimits:
    max_order_count: int
    max_position_per_ticker: int


class RiskManager:
    def __init__(self, api: KalshiAPI, limits: RiskLimits):
        self.api = api
        self.limits = limits

    def current_position(self, ticker: str) -> int:
        # Positions response structure may include multiple entries; we sum counts for the ticker.
        resp = self.api.get_positions(ticker=ticker, limit=200)
        positions = resp.get("positions", [])
        total = 0
        for p in positions:
            # Some APIs represent separate yes/no positions; treat signed exposure simply here.
            # If you want exact exposure, model YES and NO legs separately.
            total += int(p.get("position", 0)) if "position" in p else int(p.get("count", 0))
        return total

    def approve(self, intent: OrderIntent) -> Optional[str]:
        if intent.count <= 0:
            return "count<=0"
        if intent.count > self.limits.max_order_count:
            return f"count>{self.limits.max_order_count}"

        pos = self.current_position(intent.ticker)
        # naive cap: prevent absolute position from exceeding limit
        projected = abs(pos) + intent.count
        if projected > self.limits.max_position_per_ticker:
            return f"projected_position({projected})>{self.limits.max_position_per_ticker}"

        if not (1 <= intent.price_cents <= 99):
            return "price must be 1..99 cents"

        if intent.side not in ("yes", "no") or intent.action not in ("buy", "sell"):
            return "invalid side/action"

        return None
