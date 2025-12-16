from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from .kalshi.api import KalshiAPI
from .models import OrderIntent
from .risk import RiskManager
from .database import Database, OrderRecord
from .monitoring import MonitoringSystem
from .logging_config import get_logger

logger = get_logger("execution")


@dataclass
class ExecutionResult:
    intent: OrderIntent
    ok: bool
    detail: str


class Executor:
    def __init__(
        self,
        api: KalshiAPI,
        risk: RiskManager,
        paper: bool = False,
        db: Optional[Database] = None,
        monitoring: Optional[MonitoringSystem] = None,
    ):
        self.api = api
        self.risk = risk
        self.paper = paper
        self.db = db
        self.monitoring = monitoring

    def execute(self, intents: List[OrderIntent]) -> List[ExecutionResult]:
        results: List[ExecutionResult] = []
        for it in intents:
            start_time = datetime.utcnow()
            
            reject = self.risk.approve(it)
            if reject:
                result = ExecutionResult(it, False, f"RISK_REJECT: {reject}")
                results.append(result)
                
                # Log to database
                if self.db:
                    self._save_order_record(it, "rejected", error=reject)
                
                logger.warning(f"Order rejected: {it.ticker} {it.action} {it.side} - {reject}")
                continue

            if self.paper:
                result = ExecutionResult(it, True, "PAPER_OK (no order sent)")
                results.append(result)
                
                # Log to database even in paper mode
                if self.db:
                    self._save_order_record(it, "pending", paper=True)
                
                logger.info(f"Paper trade: {it.ticker} {it.action} {it.side} {it.count}@{it.price_cents}c")
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
                    post_only=it.post_only,
                    reduce_only=it.reduce_only,
                )
                order_id = resp.get("order", {}).get("order_id", "unknown")
                result = ExecutionResult(it, True, f"ORDER_SENT order_id={order_id}")
                results.append(result)
                
                # Log to database
                if self.db:
                    self._save_order_record(it, "pending", order_id=order_id, client_order_id=client_id)
                
                # Monitor execution time
                if self.monitoring:
                    self.monitoring.monitor_order_execution(order_id, start_time)
                
                logger.info(f"Order sent: {order_id} {it.ticker} {it.action} {it.side} {it.count}@{it.price_cents}c")
                
            except Exception as e:
                result = ExecutionResult(it, False, f"EXEC_ERROR: {e}")
                results.append(result)
                
                # Log error to database
                if self.db:
                    self._save_order_record(it, "rejected", error=str(e))
                
                logger.error(f"Order execution failed: {it.ticker} {it.action} {it.side} - {e}")
                
                # Send alert
                if self.monitoring:
                    self.monitoring.send_alert("error", f"Order execution failed: {e}", {
                        "ticker": it.ticker,
                        "side": it.side,
                        "action": it.action,
                    })
        
        return results
    
    def _save_order_record(
        self,
        intent: OrderIntent,
        status: str,
        order_id: Optional[str] = None,
        client_order_id: Optional[str] = None,
        error: Optional[str] = None,
        paper: bool = False,
    ):
        """Save order record to database"""
        if not self.db:
            return
        
        record = OrderRecord(
            order_id=order_id,
            client_order_id=client_order_id or intent.client_order_id or f"paper-{uuid.uuid4().hex[:16]}",
            ticker=intent.ticker,
            side=intent.side,
            action=intent.action,
            count=intent.count,
            price_cents=intent.price_cents,
            status=status,
            created_at=datetime.utcnow(),
            reason=intent.reason,
            error=error,
        )
        
        try:
            self.db.save_order(record)
        except Exception as e:
            logger.error(f"Failed to save order to database: {e}")
