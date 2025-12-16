"""
Backtesting framework for testing strategies on historical market data.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

from .database import Database
from .strategy import Strategy, MarketSnapshot
from .models import OrderIntent
from .fees import net_ev_per_contract
from .logging_config import get_logger

logger = get_logger("backtest")


@dataclass
class BacktestResult:
    """Results of a backtest"""
    start_date: datetime
    end_date: datetime
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_pnl: float
    total_fees: float
    net_pnl: float
    win_rate: float
    avg_win: float
    avg_loss: float
    sharpe_ratio: float
    max_drawdown: float
    trades: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class BacktestTrade:
    """A single trade in backtest"""
    ticker: str
    side: str
    action: str
    entry_price: int
    exit_price: Optional[int]
    count: int
    entry_time: datetime
    exit_time: Optional[datetime]
    pnl: float
    fees: float
    net_pnl: float
    filled: bool = False


class BacktestEngine:
    """Engine for running backtests on historical data"""
    
    def __init__(self, db: Database):
        self.db = db
    
    def run_backtest(
        self,
        strategy: Strategy,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
        initial_capital: float = 10000.0,
        fee_kind: str = "taker",
        taker_fee_rate: float = 0.07,
        maker_fee_rate: float = 0.0175,
    ) -> BacktestResult:
        """
        Run a backtest on historical data.
        
        Args:
            strategy: Strategy to test
            ticker: Market ticker to test
            start_date: Start date for backtest
            end_date: End date for backtest
            initial_capital: Starting capital
            fee_kind: Type of fee (taker/maker/none)
            taker_fee_rate: Taker fee rate
            maker_fee_rate: Maker fee rate
        
        Returns:
            BacktestResult with performance metrics
        """
        logger.info(f"Starting backtest for {ticker} from {start_date} to {end_date}")
        
        # Get historical snapshots
        snapshots = self.db.get_market_snapshots(ticker, start_date, end_date)
        
        if not snapshots:
            logger.warning(f"No historical data found for {ticker}")
            return BacktestResult(
                start_date=start_date,
                end_date=end_date,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                total_pnl=0.0,
                total_fees=0.0,
                net_pnl=0.0,
                win_rate=0.0,
                avg_win=0.0,
                avg_loss=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
            )
        
        # Simulate trading
        trades: List[BacktestTrade] = []
        current_capital = initial_capital
        positions: Dict[str, BacktestTrade] = {}  # ticker -> open position
        
        for snapshot in snapshots:
            timestamp = datetime.fromisoformat(snapshot["timestamp"])
            
            # Create market snapshot
            from .kalshi.api import BestPrices
            best = BestPrices(
                yes_bid=snapshot.get("yes_bid"),
                yes_ask=snapshot.get("yes_ask"),
                no_bid=snapshot.get("no_bid"),
                no_ask=snapshot.get("no_ask"),
            )
            market_snap = MarketSnapshot(ticker=ticker, best=best)
            
            # Get strategy signals
            intents = strategy.generate([market_snap])
            
            # Execute trades
            for intent in intents:
                trade = self._execute_trade(
                    intent,
                    timestamp,
                    best,
                    fee_kind,
                    taker_fee_rate,
                    maker_fee_rate,
                )
                
                if trade:
                    # Check if we have an open position
                    position_key = f"{intent.ticker}_{intent.side}"
                    if position_key in positions:
                        # Close existing position
                        open_trade = positions.pop(position_key)
                        open_trade.exit_price = trade.entry_price
                        open_trade.exit_time = timestamp
                        open_trade.pnl = self._calculate_pnl(open_trade)
                        open_trade.fees += trade.fees
                        open_trade.net_pnl = open_trade.pnl - open_trade.fees
                        trades.append(open_trade)
                    
                    # Open new position
                    positions[position_key] = trade
        
        # Close remaining positions at end
        for trade in positions.values():
            if trade.exit_price is None:
                # Use last snapshot price
                last_snapshot = snapshots[-1]
                if trade.side == "yes":
                    trade.exit_price = last_snapshot.get("yes_bid") or last_snapshot.get("yes_ask")
                else:
                    trade.exit_price = last_snapshot.get("no_bid") or last_snapshot.get("no_ask")
                trade.exit_time = datetime.fromisoformat(last_snapshot["timestamp"])
                trade.pnl = self._calculate_pnl(trade)
                trade.net_pnl = trade.pnl - trade.fees
            trades.append(trade)
        
        # Calculate statistics
        return self._calculate_results(trades, start_date, end_date)
    
    def _execute_trade(
        self,
        intent: OrderIntent,
        timestamp: datetime,
        best: "BestPrices",
        fee_kind: str,
        taker_fee_rate: float,
        maker_fee_rate: float,
    ) -> Optional[BacktestTrade]:
        """Execute a trade in backtest"""
        # Determine fill price
        if intent.side == "yes":
            fill_price = best.yes_ask if best.yes_ask else best.yes_bid
        else:
            fill_price = best.no_ask if best.no_ask else best.no_bid
        
        if fill_price is None:
            return None
        
        # Calculate fees
        fee_rate = taker_fee_rate if fee_kind == "taker" else (maker_fee_rate if fee_kind == "maker" else 0.0)
        fees = intent.count * fill_price * fee_rate / 100.0
        
        return BacktestTrade(
            ticker=intent.ticker,
            side=intent.side,
            action=intent.action,
            entry_price=fill_price,
            exit_price=None,
            count=intent.count,
            entry_time=timestamp,
            exit_time=None,
            pnl=0.0,
            fees=fees,
            net_pnl=0.0,
            filled=True,
        )
    
    def _calculate_pnl(self, trade: BacktestTrade) -> float:
        """Calculate P&L for a trade"""
        if trade.exit_price is None:
            return 0.0
        
        if trade.side == "yes":
            # YES contract: profit if exit > entry
            pnl_per_contract = (trade.exit_price - trade.entry_price) / 100.0
        else:
            # NO contract: profit if exit < entry (inverted)
            pnl_per_contract = (trade.entry_price - trade.exit_price) / 100.0
        
        return pnl_per_contract * trade.count
    
    def _calculate_results(self, trades: List[BacktestTrade], start_date: datetime, end_date: datetime) -> BacktestResult:
        """Calculate backtest statistics"""
        if not trades:
            return BacktestResult(
                start_date=start_date,
                end_date=end_date,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                total_pnl=0.0,
                total_fees=0.0,
                net_pnl=0.0,
                win_rate=0.0,
                avg_win=0.0,
                avg_loss=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
            )
        
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t.net_pnl > 0)
        losing_trades = sum(1 for t in trades if t.net_pnl < 0)
        
        total_pnl = sum(t.pnl for t in trades)
        total_fees = sum(t.fees for t in trades)
        net_pnl = total_pnl - total_fees
        
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        
        wins = [t.net_pnl for t in trades if t.net_pnl > 0]
        losses = [t.net_pnl for t in trades if t.net_pnl < 0]
        
        avg_win = sum(wins) / len(wins) if wins else 0.0
        avg_loss = sum(losses) / len(losses) if losses else 0.0
        
        # Calculate Sharpe ratio (simplified)
        returns = [t.net_pnl for t in trades]
        if returns:
            avg_return = sum(returns) / len(returns)
            variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
            std_dev = variance ** 0.5
            sharpe_ratio = avg_return / std_dev if std_dev > 0 else 0.0
        else:
            sharpe_ratio = 0.0
        
        # Calculate max drawdown
        cumulative_pnl = 0.0
        peak = 0.0
        max_drawdown = 0.0
        for trade in trades:
            cumulative_pnl += trade.net_pnl
            if cumulative_pnl > peak:
                peak = cumulative_pnl
            drawdown = peak - cumulative_pnl
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        return BacktestResult(
            start_date=start_date,
            end_date=end_date,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            total_pnl=total_pnl,
            total_fees=total_fees,
            net_pnl=net_pnl,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            trades=[self._trade_to_dict(t) for t in trades],
        )
    
    def _trade_to_dict(self, trade: BacktestTrade) -> Dict[str, Any]:
        """Convert trade to dictionary"""
        return {
            "ticker": trade.ticker,
            "side": trade.side,
            "action": trade.action,
            "entry_price": trade.entry_price,
            "exit_price": trade.exit_price,
            "count": trade.count,
            "entry_time": trade.entry_time.isoformat(),
            "exit_time": trade.exit_time.isoformat() if trade.exit_time else None,
            "pnl": trade.pnl,
            "fees": trade.fees,
            "net_pnl": trade.net_pnl,
        }

