"""
Order management system for tracking, canceling, and modifying orders.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from .kalshi.api import KalshiAPI
from .database import Database, OrderRecord
from .logging_config import get_logger

logger = get_logger("order_manager")


@dataclass
class OrderStatus:
    """Current status of an order"""
    order_id: str
    client_order_id: str
    ticker: str
    side: str
    action: str
    count: int
    price_cents: int
    status: str  # pending, filled, cancelled, rejected
    filled_count: int
    remaining_count: int
    created_at: datetime


class OrderManager:
    """Manages order lifecycle: creation, tracking, cancellation, modification"""
    
    def __init__(self, api: KalshiAPI, db: Database):
        self.api = api
        self.db = db
    
    def get_active_orders(self, ticker: Optional[str] = None) -> List[OrderStatus]:
        """Get all active (pending) orders"""
        orders = self.db.get_orders(ticker=ticker, status="pending")
        return [self._order_to_status(o) for o in orders]
    
    def get_order_status(self, order_id: str) -> Optional[OrderStatus]:
        """Get status of a specific order"""
        orders = self.db.get_orders()
        for order in orders:
            if order.get("order_id") == order_id or order.get("client_order_id") == order_id:
                return self._order_to_status(order)
        return None
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        try:
            # Try to cancel via API
            self.api.cancel_order(order_id)
            
            # Update database
            self.db.update_order_status(order_id, "cancelled")
            logger.info(f"Order {order_id} cancelled successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            self.db.update_order_status(order_id, "cancelled", error=str(e))
            return False
    
    def cancel_all_orders(self, ticker: Optional[str] = None) -> int:
        """Cancel all active orders, optionally filtered by ticker"""
        active_orders = self.get_active_orders(ticker=ticker)
        cancelled_count = 0
        
        for order in active_orders:
            if self.cancel_order(order.order_id):
                cancelled_count += 1
        
        logger.info(f"Cancelled {cancelled_count} orders")
        return cancelled_count
    
    def get_order_history(
        self,
        ticker: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get order history"""
        return self.db.get_orders(ticker=ticker, limit=limit)
    
    def get_fills_for_order(self, order_id: str) -> List[Dict[str, Any]]:
        """Get all fills for a specific order"""
        return self.db.get_fills(order_id=order_id)
    
    def sync_order_status(self, order_id: str) -> Optional[OrderStatus]:
        """Sync order status from API and update database"""
        try:
            # Get orders from API
            api_orders = self.api.get_orders(status="pending", limit=1000)
            orders = api_orders.get("orders", [])
            
            # Find matching order
            for api_order in orders:
                if api_order.get("order_id") == order_id:
                    # Update database with current status
                    status = api_order.get("status", "unknown")
                    filled_count = api_order.get("filled_count", 0)
                    
                    self.db.update_order_status(
                        order_id,
                        status,
                        filled_count=filled_count
                    )
                    
                    logger.debug(f"Synced order {order_id}: status={status}, filled={filled_count}")
                    return self.get_order_status(order_id)
            
            # Order not found in API, might be filled or cancelled
            logger.warning(f"Order {order_id} not found in API, marking as unknown")
            return None
            
        except Exception as e:
            logger.error(f"Failed to sync order {order_id}: {e}")
            return None
    
    def sync_all_orders(self) -> Dict[str, int]:
        """Sync all orders from API"""
        stats = {"synced": 0, "errors": 0}
        
        try:
            api_orders = self.api.get_orders(limit=1000)
            orders = api_orders.get("orders", [])
            
            for api_order in orders:
                try:
                    order_id = api_order.get("order_id")
                    if order_id:
                        self.sync_order_status(order_id)
                        stats["synced"] += 1
                except Exception as e:
                    logger.error(f"Error syncing order: {e}")
                    stats["errors"] += 1
            
            logger.info(f"Synced {stats['synced']} orders, {stats['errors']} errors")
        except Exception as e:
            logger.error(f"Failed to sync orders: {e}")
            stats["errors"] += 1
        
        return stats
    
    def _order_to_status(self, order_dict: Dict[str, Any]) -> OrderStatus:
        """Convert database order dict to OrderStatus"""
        filled_count = order_dict.get("filled_count") or 0
        total_count = order_dict.get("count", 0)
        
        return OrderStatus(
            order_id=order_dict.get("order_id", ""),
            client_order_id=order_dict.get("client_order_id", ""),
            ticker=order_dict.get("ticker", ""),
            side=order_dict.get("side", ""),
            action=order_dict.get("action", ""),
            count=total_count,
            price_cents=order_dict.get("price_cents", 0),
            status=order_dict.get("status", "unknown"),
            filled_count=filled_count,
            remaining_count=total_count - filled_count,
            created_at=datetime.fromisoformat(order_dict.get("created_at", ""))
        )

