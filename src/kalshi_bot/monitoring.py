"""
Monitoring and alerting system for the trading bot.
Tracks key metrics and sends alerts on anomalies.
"""
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from collections import deque

from .database import Database
from .logging_config import get_logger

logger = get_logger("monitoring")


@dataclass
class Alert:
    """Alert message"""
    level: str  # info, warning, error, critical
    message: str
    timestamp: datetime
    metadata: Dict = field(default_factory=dict)


@dataclass
class Metric:
    """Performance metric"""
    name: str
    value: float
    timestamp: datetime
    tags: Dict = field(default_factory=dict)


class AlertHandler:
    """Base class for alert handlers"""
    
    def handle(self, alert: Alert) -> None:
        """Handle an alert"""
        raise NotImplementedError


class LoggingAlertHandler(AlertHandler):
    """Alert handler that logs alerts"""
    
    def handle(self, alert: Alert) -> None:
        level = alert.level.upper()
        msg = f"[ALERT {level}] {alert.message}"
        if alert.metadata:
            msg += f" | Metadata: {alert.metadata}"
        
        if alert.level == "critical":
            logger.critical(msg)
        elif alert.level == "error":
            logger.error(msg)
        elif alert.level == "warning":
            logger.warning(msg)
        else:
            logger.info(msg)


class MonitoringSystem:
    """Monitors trading bot performance and sends alerts"""
    
    def __init__(self, db: Database, alert_handlers: Optional[List[AlertHandler]] = None):
        self.db = db
        self.alert_handlers = alert_handlers or [LoggingAlertHandler()]
        
        # Metric tracking
        self.metrics_buffer: deque = deque(maxlen=1000)
        self.last_check_time = datetime.utcnow()
        
        # Thresholds
        self.thresholds = {
            "error_rate": 0.1,  # 10% error rate
            "order_fill_rate": 0.5,  # 50% fill rate minimum
            "latency_ms": 5000,  # 5 seconds max latency
            "position_limit": 0.9,  # 90% of max position
        }
    
    def record_metric(self, name: str, value: float, tags: Optional[Dict] = None):
        """Record a performance metric"""
        metric = Metric(
            name=name,
            value=value,
            timestamp=datetime.utcnow(),
            tags=tags or {}
        )
        self.metrics_buffer.append(metric)
        self.db.save_performance_metric(name, value, tags)
    
    def send_alert(self, level: str, message: str, metadata: Optional[Dict] = None):
        """Send an alert"""
        alert = Alert(
            level=level,
            message=message,
            timestamp=datetime.utcnow(),
            metadata=metadata or {}
        )
        
        for handler in self.alert_handlers:
            try:
                handler.handle(alert)
            except Exception as e:
                logger.error(f"Alert handler failed: {e}")
    
    def check_health(self) -> Dict[str, Any]:
        """Perform health check and return status"""
        health = {
            "status": "healthy",
            "timestamp": datetime.utcnow(),
            "checks": {}
        }
        
        # Check recent orders
        recent_orders = self.db.get_orders(limit=100)
        if recent_orders:
            total_orders = len(recent_orders)
            error_orders = sum(1 for o in recent_orders if o.get("status") == "rejected")
            error_rate = error_orders / total_orders if total_orders > 0 else 0
            
            health["checks"]["order_error_rate"] = {
                "value": error_rate,
                "status": "ok" if error_rate < self.thresholds["error_rate"] else "warning"
            }
            
            if error_rate > self.thresholds["error_rate"]:
                self.send_alert(
                    "warning",
                    f"High error rate: {error_rate:.2%}",
                    {"error_rate": error_rate, "total_orders": total_orders}
                )
        
        # Check database connectivity
        try:
            self.db.get_orders(limit=1)
            health["checks"]["database"] = {"status": "ok"}
        except Exception as e:
            health["checks"]["database"] = {"status": "error", "error": str(e)}
            health["status"] = "unhealthy"
            self.send_alert("error", f"Database connectivity issue: {e}")
        
        # Check recent metrics
        if self.metrics_buffer:
            recent_metrics = list(self.metrics_buffer)[-100:]
            latency_metrics = [m for m in recent_metrics if "latency" in m.name.lower()]
            if latency_metrics:
                avg_latency = sum(m.value for m in latency_metrics) / len(latency_metrics)
                health["checks"]["avg_latency_ms"] = {
                    "value": avg_latency,
                    "status": "ok" if avg_latency < self.thresholds["latency_ms"] else "warning"
                }
        
        return health
    
    def get_metrics_summary(self, minutes: int = 60) -> Dict[str, Any]:
        """Get metrics summary for the last N minutes"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        # Get metrics from buffer
        recent_metrics = [
            m for m in self.metrics_buffer
            if m.timestamp >= cutoff_time
        ]
        
        # Group by metric name
        metrics_by_name: Dict[str, List[float]] = {}
        for metric in recent_metrics:
            if metric.name not in metrics_by_name:
                metrics_by_name[metric.name] = []
            metrics_by_name[metric.name].append(metric.value)
        
        # Calculate statistics
        summary = {}
        for name, values in metrics_by_name.items():
            if values:
                summary[name] = {
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                }
        
        return summary
    
    def monitor_order_execution(self, order_id: str, start_time: datetime):
        """Monitor order execution time"""
        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        self.record_metric("order_execution_latency_ms", execution_time, {"order_id": order_id})
        
        if execution_time > self.thresholds["latency_ms"]:
            self.send_alert(
                "warning",
                f"Slow order execution: {execution_time:.0f}ms",
                {"order_id": order_id, "latency_ms": execution_time}
            )

