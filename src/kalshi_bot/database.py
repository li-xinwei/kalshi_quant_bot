"""
Database layer for persisting orders, fills, and trading data.
Uses SQLite by default, but can be extended to PostgreSQL.
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from .models import OrderIntent


@dataclass
class OrderRecord:
    """Database record for an order"""
    order_id: Optional[str]
    client_order_id: str
    ticker: str
    side: str
    action: str
    count: int
    price_cents: int
    status: str  # pending, filled, cancelled, rejected
    created_at: datetime
    filled_at: Optional[datetime] = None
    filled_price: Optional[int] = None
    filled_count: Optional[int] = None
    reason: Optional[str] = None
    error: Optional[str] = None


@dataclass
class FillRecord:
    """Database record for a fill"""
    fill_id: str
    order_id: str
    ticker: str
    side: str
    price_cents: int
    count: int
    filled_at: datetime
    fee: Optional[float] = None


class Database:
    """Database interface for trading data"""
    
    def __init__(self, db_path: str = "kalshi_bot.db"):
        self.db_path = Path(db_path)
        self.conn: Optional[sqlite3.Connection] = None
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema"""
        self.conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            timeout=30.0
        )
        self.conn.row_factory = sqlite3.Row
        
        cursor = self.conn.cursor()
        
        # Orders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                client_order_id TEXT UNIQUE NOT NULL,
                ticker TEXT NOT NULL,
                side TEXT NOT NULL,
                action TEXT NOT NULL,
                count INTEGER NOT NULL,
                price_cents INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                filled_at TIMESTAMP,
                filled_price INTEGER,
                filled_count INTEGER,
                reason TEXT,
                error TEXT
            )
        """)
        
        # Fills table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fills (
                fill_id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                ticker TEXT NOT NULL,
                side TEXT NOT NULL,
                price_cents INTEGER NOT NULL,
                count INTEGER NOT NULL,
                filled_at TIMESTAMP NOT NULL,
                fee REAL,
                FOREIGN KEY (order_id) REFERENCES orders(order_id)
            )
        """)
        
        # Market snapshots table (for backtesting)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                yes_bid INTEGER,
                yes_ask INTEGER,
                no_bid INTEGER,
                no_ask INTEGER,
                snapshot_data TEXT  -- JSON data
            )
        """)
        
        # Performance metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                metadata TEXT  -- JSON data
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_ticker ON orders(ticker)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fills_order_id ON fills(order_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fills_ticker ON fills(ticker)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_ticker ON market_snapshots(ticker)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp ON market_snapshots(timestamp)")
        
        self.conn.commit()
    
    def save_order(self, order: OrderRecord) -> None:
        """Save an order to the database"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO orders 
            (order_id, client_order_id, ticker, side, action, count, price_cents,
             status, created_at, filled_at, filled_price, filled_count, reason, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order.order_id,
            order.client_order_id,
            order.ticker,
            order.side,
            order.action,
            order.count,
            order.price_cents,
            order.status,
            order.created_at,
            order.filled_at,
            order.filled_price,
            order.filled_count,
            order.reason,
            order.error
        ))
        self.conn.commit()
    
    def update_order_status(
        self,
        order_id: str,
        status: str,
        filled_at: Optional[datetime] = None,
        filled_price: Optional[int] = None,
        filled_count: Optional[int] = None,
        error: Optional[str] = None
    ) -> None:
        """Update order status"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE orders 
            SET status = ?, filled_at = ?, filled_price = ?, filled_count = ?, error = ?
            WHERE order_id = ?
        """, (status, filled_at, filled_price, filled_count, error, order_id))
        self.conn.commit()
    
    def save_fill(self, fill: FillRecord) -> None:
        """Save a fill to the database"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO fills 
            (fill_id, order_id, ticker, side, price_cents, count, filled_at, fee)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            fill.fill_id,
            fill.order_id,
            fill.ticker,
            fill.side,
            fill.price_cents,
            fill.count,
            fill.filled_at,
            fill.fee
        ))
        self.conn.commit()
    
    def save_market_snapshot(
        self,
        ticker: str,
        yes_bid: Optional[int],
        yes_ask: Optional[int],
        no_bid: Optional[int],
        no_ask: Optional[int],
        snapshot_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Save a market snapshot for backtesting"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO market_snapshots 
            (ticker, timestamp, yes_bid, yes_ask, no_bid, no_ask, snapshot_data)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            ticker,
            datetime.utcnow(),
            yes_bid,
            yes_ask,
            no_bid,
            no_ask,
            json.dumps(snapshot_data) if snapshot_data else None
        ))
        self.conn.commit()
    
    def save_performance_metric(
        self,
        metric_name: str,
        metric_value: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Save a performance metric"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO performance_metrics 
            (timestamp, metric_name, metric_value, metadata)
            VALUES (?, ?, ?, ?)
        """, (
            datetime.utcnow(),
            metric_name,
            metric_value,
            json.dumps(metadata) if metadata else None
        ))
        self.conn.commit()
    
    def get_orders(
        self,
        ticker: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get orders with optional filters"""
        cursor = self.conn.cursor()
        query = "SELECT * FROM orders WHERE 1=1"
        params = []
        
        if ticker:
            query += " AND ticker = ?"
            params.append(ticker)
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_fills(
        self,
        order_id: Optional[str] = None,
        ticker: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get fills with optional filters"""
        cursor = self.conn.cursor()
        query = "SELECT * FROM fills WHERE 1=1"
        params = []
        
        if order_id:
            query += " AND order_id = ?"
            params.append(order_id)
        if ticker:
            query += " AND ticker = ?"
            params.append(ticker)
        
        query += " ORDER BY filled_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_market_snapshots(
        self,
        ticker: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Get market snapshots for backtesting"""
        cursor = self.conn.cursor()
        query = "SELECT * FROM market_snapshots WHERE ticker = ?"
        params = [ticker]
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)
        
        query += " ORDER BY timestamp ASC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

