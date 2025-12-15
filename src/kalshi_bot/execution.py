from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import List

from .kalshi.api import KalshiAPI
from .models import OrderIntent
from .risk import RiskManager


@dataclass
class ExecutionResult:
    intent: OrderIntent
    ok: bool
    detail: str


class Executor:
    def __init__(self, api: KalshiAPI, risk: RiskManager, paper: bool = False):
        self.api = api
        self.risk = risk
        self.paper = paper

    def execute(self, intents: List[OrderIntent]) -> List[ExecutionResult]:
        results: List[ExecutionResult] = []
        for it in intents:
            reject = self.risk.approve(it)
            if reject:
                results.append(ExecutionResult(it, False, f"RISK_REJECT: {reject}"))
                continue

            if self.paper:
                results.append(ExecutionResult(it, True, "PAPER_OK (no order sent)"))
                continue

            client_id = it.client_order_id or f"bot-{uuid.uuid4().hex[:16]}"
            try:
                resp = self.api.create_limit_order(
                    ticker=it.ticker,
                    side=it.side,
                    action=it.action,
                    count=it.count,
                    price_cents=it.price_cents,
                    client_order_id=client_id,
                    post_only=True,
                )
                order_id = resp.get("order", {}).get("order_id", "unknown")
                results.append(ExecutionResult(it, True, f"ORDER_SENT order_id={order_id}"))
            except Exception as e:
                results.append(ExecutionResult(it, False, f"EXEC_ERROR: {e}"))
        return results
