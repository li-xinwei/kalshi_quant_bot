"""
Performance analysis tools for evaluating trading strategy performance.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass

from .database import Database
from .logging_config import get_logger

logger = get_logger("performance")


@dataclass
class PerformanceMetrics:
    """Performance metrics for a trading period"""
    period_start: datetime
    period_end: datetime
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    total_fees: float
    net_pnl: float
    avg_trade_pnl: float
    sharpe_ratio: float
    max_drawdown: float
    profit_factor: float
    avg_holding_time_minutes: float


class PerformanceAnalyzer:
    """Analyzes trading performance from database records"""
    
    def __init__(self, db: Database):
        self.db = db
    
    def analyze_performance(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        ticker: Optional[str] = None,
    ) -> PerformanceMetrics:
        """Analyze performance for a given period"""
        if end_date is None:
            end_date = datetime.utcnow()
        if start_date is None:
            start_date = end_date - timedelta(days=30)
        
        # Get fills
        fills = self.db.get_fills(ticker=ticker, limit=10000)
        
        if not fills:
            return PerformanceMetrics(
                period_start=start_date,
                period_end=end_date,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                total_pnl=0.0,
                total_fees=0.0,
                net_pnl=0.0,
                avg_trade_pnl=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                profit_factor=0.0,
                avg_holding_time_minutes=0.0,
            )
        
        # Filter by date
        filtered_fills = [
            f for f in fills
            if start_date <= datetime.fromisoformat(f["filled_at"]) <= end_date
        ]
        
        # Group fills by order
        orders_pnl: Dict[str, List[Dict]] = {}
        for fill in filtered_fills:
            order_id = fill["order_id"]
            if order_id not in orders_pnl:
                orders_pnl[order_id] = []
            orders_pnl[order_id].append(fill)
        
        # Calculate P&L per order
        order_results = []
        for order_id, fills_list in orders_pnl.items():
            order = self.db.get_orders()[0] if self.db.get_orders() else None
            if not order:
                continue
            
            # Calculate P&L (simplified - assumes we know entry/exit)
            # In reality, you'd need to track positions
            total_fees = sum(f.get("fee", 0) or 0 for f in fills_list)
            
            # This is a simplified calculation
            # Real implementation would track position entry/exit
            order_results.append({
                "order_id": order_id,
                "pnl": 0.0,  # Would need position tracking
                "fees": total_fees,
                "net_pnl": -total_fees,  # Simplified
            })
        
        total_trades = len(order_results)
        winning_trades = sum(1 for r in order_results if r["net_pnl"] > 0)
        losing_trades = sum(1 for r in order_results if r["net_pnl"] < 0)
        
        total_pnl = sum(r["pnl"] for r in order_results)
        total_fees = sum(r["fees"] for r in order_results)
        net_pnl = total_pnl - total_fees
        
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        avg_trade_pnl = net_pnl / total_trades if total_trades > 0 else 0.0
        
        # Calculate Sharpe ratio
        returns = [r["net_pnl"] for r in order_results]
        if returns:
            avg_return = sum(returns) / len(returns)
            variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
            std_dev = variance ** 0.5
            sharpe_ratio = avg_return / std_dev if std_dev > 0 else 0.0
        else:
            sharpe_ratio = 0.0
        
        # Calculate profit factor
        gross_profit = sum(r["net_pnl"] for r in order_results if r["net_pnl"] > 0)
        gross_loss = abs(sum(r["net_pnl"] for r in order_results if r["net_pnl"] < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
        
        return PerformanceMetrics(
            period_start=start_date,
            period_end=end_date,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            total_fees=total_fees,
            net_pnl=net_pnl,
            avg_trade_pnl=avg_trade_pnl,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=0.0,  # Would need cumulative P&L tracking
            profit_factor=profit_factor,
            avg_holding_time_minutes=0.0,  # Would need position tracking
        )
    
    def print_performance_report(self, metrics: PerformanceMetrics):
        """Print a formatted performance report"""
        print("\n" + "="*70)
        print("PERFORMANCE REPORT")
        print("="*70)
        print(f"Period: {metrics.period_start} to {metrics.period_end}")
        print(f"\n📊 TRADE STATISTICS:")
        print(f"  Total Trades:          {metrics.total_trades}")
        print(f"  Winning Trades:        {metrics.winning_trades}")
        print(f"  Losing Trades:         {metrics.losing_trades}")
        print(f"  Win Rate:              {metrics.win_rate:.2%}")
        
        print(f"\n💰 P&L STATISTICS:")
        print(f"  Total P&L:             ${metrics.total_pnl:.2f}")
        print(f"  Total Fees:             ${metrics.total_fees:.2f}")
        print(f"  Net P&L:                ${metrics.net_pnl:.2f}")
        print(f"  Avg Trade P&L:         ${metrics.avg_trade_pnl:.2f}")
        
        print(f"\n📈 RISK METRICS:")
        print(f"  Sharpe Ratio:           {metrics.sharpe_ratio:.2f}")
        print(f"  Max Drawdown:           ${metrics.max_drawdown:.2f}")
        print(f"  Profit Factor:          {metrics.profit_factor:.2f}")
        
        print("="*70 + "\n")

