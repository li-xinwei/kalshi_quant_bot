#!/usr/bin/env python3
"""
Simulate trading and collect statistics.
Usage: python simulate_trades.py [--loops N] [--paper]
"""
import argparse
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from kalshi_bot.config import BotConfig
from kalshi_bot.kalshi.auth import KalshiSigner
from kalshi_bot.kalshi.http import KalshiHTTPClient, RateLimiter
from kalshi_bot.kalshi.api import KalshiAPI
from kalshi_bot.strategy import MarketSnapshot, FeeAwareFairValueStrategy, FeeAwareConfig
from kalshi_bot.fair_prob import StaticFairProbProvider, LiveDataWinProbProvider
from kalshi_bot.risk import RiskManager, RiskLimits
from kalshi_bot.execution import Executor, ExecutionResult
from kalshi_bot.models import OrderIntent


@dataclass
class TradeStats:
    """Statistics for a single trade intent"""
    ticker: str
    side: str
    action: str
    price_cents: int
    count: int
    edge: float = 0.0
    net_ev: float = 0.0
    fair_prob: float = 0.0
    market_price: float = 0.0
    reason: str = ""
    executed: bool = False
    rejected: bool = False
    rejection_reason: str = ""


@dataclass
class SimulationStats:
    """Overall simulation statistics"""
    total_loops: int = 0
    total_intents: int = 0
    total_executed: int = 0
    total_rejected: int = 0
    total_paper_ok: int = 0
    
    # Price statistics
    avg_price: float = 0.0
    min_price: int = 99
    max_price: int = 1
    
    # Edge statistics
    avg_edge: float = 0.0
    min_edge: float = 1.0
    max_edge: float = -1.0
    total_edge: float = 0.0
    
    # EV statistics
    avg_net_ev: float = 0.0
    total_net_ev: float = 0.0
    min_net_ev: float = 0.0
    max_net_ev: float = 0.0
    
    # By ticker
    trades_by_ticker: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    # By side
    trades_by_side: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    # Rejection reasons
    rejection_reasons: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    # Market data
    market_snapshots: int = 0
    market_errors: int = 0
    
    def add_trade(self, intent: OrderIntent, result: ExecutionResult, edge: float = 0.0, net_ev: float = 0.0, fair_prob: float = 0.0):
        """Add a trade to statistics"""
        self.total_intents += 1
        self.trades_by_ticker[intent.ticker] += 1
        self.trades_by_side[f"{intent.side}_{intent.action}"] += 1
        
        # Price stats
        self.avg_price = (self.avg_price * (self.total_intents - 1) + intent.price_cents) / self.total_intents
        self.min_price = min(self.min_price, intent.price_cents)
        self.max_price = max(self.max_price, intent.price_cents)
        
        # Edge stats
        self.total_edge += edge
        self.avg_edge = self.total_edge / self.total_intents
        self.min_edge = min(self.min_edge, edge)
        self.max_edge = max(self.max_edge, edge)
        
        # EV stats
        self.total_net_ev += net_ev
        self.avg_net_ev = self.total_net_ev / self.total_intents
        if self.total_intents == 1:
            self.min_net_ev = net_ev
            self.max_net_ev = net_ev
        else:
            self.min_net_ev = min(self.min_net_ev, net_ev)
            self.max_net_ev = max(self.max_net_ev, net_ev)
        
        # Execution stats
        if result.ok:
            self.total_executed += 1
            if "PAPER_OK" in result.detail:
                self.total_paper_ok += 1
        else:
            self.total_rejected += 1
            if "RISK_REJECT" in result.detail:
                reason = result.detail.replace("RISK_REJECT: ", "")
                self.rejection_reasons[reason] += 1
    
    def print_report(self):
        """Print a formatted statistics report"""
        print("\n" + "="*70)
        print("TRADING SIMULATION STATISTICS")
        print("="*70)
        
        print(f"\n📊 OVERALL STATISTICS:")
        print(f"  Total Loops:           {self.total_loops}")
        print(f"  Market Snapshots:      {self.market_snapshots}")
        print(f"  Market Errors:         {self.market_errors}")
        print(f"  Total Trade Intents:   {self.total_intents}")
        print(f"  Executed:              {self.total_executed} ({self.total_executed/self.total_intents*100:.1f}%)" if self.total_intents > 0 else "  Executed:              0")
        print(f"  Rejected:              {self.total_rejected} ({self.total_rejected/self.total_intents*100:.1f}%)" if self.total_intents > 0 else "  Rejected:              0")
        print(f"  Paper OK:              {self.total_paper_ok}")
        
        if self.total_intents > 0:
            print(f"\n💰 PRICE STATISTICS:")
            print(f"  Average Price:         {self.avg_price:.2f}c")
            print(f"  Min Price:             {self.min_price}c")
            print(f"  Max Price:             {self.max_price}c")
            
            print(f"\n📈 EDGE STATISTICS:")
            print(f"  Average Edge:           {self.avg_edge:.4f} ({self.avg_edge*100:.2f}%)")
            print(f"  Min Edge:               {self.min_edge:.4f} ({self.min_edge*100:.2f}%)")
            print(f"  Max Edge:               {self.max_edge:.4f} ({self.max_edge*100:.2f}%)")
            print(f"  Total Edge:             {self.total_edge:.4f} ({self.total_edge*100:.2f}%)")
            
            print(f"\n💵 NET EV STATISTICS:")
            print(f"  Average Net EV:        ${self.avg_net_ev:.4f}")
            print(f"  Min Net EV:            ${self.min_net_ev:.4f}")
            print(f"  Max Net EV:            ${self.max_net_ev:.4f}")
            print(f"  Total Net EV:          ${self.total_net_ev:.4f}")
        
        if self.trades_by_ticker:
            print(f"\n📋 TRADES BY TICKER:")
            for ticker, count in sorted(self.trades_by_ticker.items(), key=lambda x: x[1], reverse=True):
                print(f"  {ticker}: {count} trades")
        
        if self.trades_by_side:
            print(f"\n🔄 TRADES BY SIDE:")
            for side_action, count in sorted(self.trades_by_side.items(), key=lambda x: x[1], reverse=True):
                print(f"  {side_action}: {count} trades")
        
        if self.rejection_reasons:
            print(f"\n❌ REJECTION REASONS:")
            for reason, count in sorted(self.rejection_reasons.items(), key=lambda x: x[1], reverse=True):
                print(f"  {reason}: {count} times")
        
        print("\n" + "="*70)


def extract_edge_from_reason(reason: str) -> tuple[float, float]:
    """Extract edge and net_ev from reason string"""
    edge = 0.0
    net_ev = 0.0
    try:
        # Format: "YES netEV=0.0050 edge=0.015 fair=0.995"
        if "edge=" in reason:
            edge_str = reason.split("edge=")[1].split()[0]
            edge = float(edge_str)
        if "netEV=" in reason:
            ev_str = reason.split("netEV=")[1].split()[0]
            net_ev = float(ev_str)
    except:
        pass
    return edge, net_ev


def extract_fair_prob_from_reason(reason: str) -> float:
    """Extract fair probability from reason string"""
    try:
        if "fair=" in reason:
            fair_str = reason.split("fair=")[1].split()[0]
            return float(fair_str)
    except:
        pass
    return 0.0


def main():
    parser = argparse.ArgumentParser(description='Simulate trading and collect statistics')
    parser.add_argument('--loops', type=int, default=100, help='Number of loops to run')
    parser.add_argument('--paper', action='store_true', help='Paper trade mode')
    parser.add_argument('--fast', action='store_true', help='Fast mode: reduce sleep time to 0.1s')
    args = parser.parse_args()

    cfg = BotConfig.load()
    stats = SimulationStats()

    signer = KalshiSigner.from_pem_file(cfg.api_key_id, cfg.private_key_path)
    http = KalshiHTTPClient(
        host=cfg.host,
        signer=signer,
        read_rl=RateLimiter(per_second=15.0),
        write_rl=RateLimiter(per_second=8.0),
        timeout_s=10.0,
    )
    api = KalshiAPI(http)

    provider = (
        LiveDataWinProbProvider(
            api=api,
            fair_probs_yes=cfg.fair_probs,
            coef_score_diff=cfg.coef_score_diff,
            coef_time_left_min=cfg.coef_time_left_min,
            coef_prior=cfg.coef_prior,
        )
        if cfg.use_live_data
        else StaticFairProbProvider(cfg.fair_probs)
    )

    strat = FeeAwareFairValueStrategy(
        FeeAwareConfig(
            edge_threshold=cfg.edge_threshold,
            fee_kind=cfg.fee_kind,
            taker_fee_rate=cfg.taker_fee_rate,
            maker_fee_rate=cfg.maker_fee_rate,
            min_net_ev_per_contract=cfg.min_net_ev_per_contract,
            post_only=cfg.post_only,
        ),
        provider=provider,
        order_count=min(5, cfg.max_order_count),
    )

    risk = RiskManager(api, RiskLimits(cfg.max_order_count, cfg.max_position_per_ticker))
    exe = Executor(api, risk, paper=args.paper)

    print(f"[Simulation] Running {args.loops} loops")
    print(f"[Simulation] env={cfg.env} paper={args.paper}")
    print(f"[Simulation] tickers={cfg.tickers}")
    print(f"[Simulation] fair_probs={cfg.fair_probs}")
    print(f"[Simulation] edge_threshold={cfg.edge_threshold}")
    print()

    try:
        for loop in range(1, args.loops + 1):
            stats.total_loops = loop
            
            snaps: List[MarketSnapshot] = []
            for t in cfg.tickers:
                try:
                    ob = api.get_orderbook(t, depth=10)
                    best = api.best_prices_from_orderbook(ob)
                    snaps.append(MarketSnapshot(ticker=t, best=best))
                    stats.market_snapshots += 1
                except Exception as e:
                    stats.market_errors += 1
                    if loop % 10 == 0:  # Only print errors every 10 loops
                        print(f"[data] {t}: error - {e}")

            intents = strat.generate(snaps)
            
            if intents:
                results = exe.execute(intents)
                for intent, result in zip(intents, results):
                    edge, net_ev = extract_edge_from_reason(intent.reason)
                    fair_prob = extract_fair_prob_from_reason(intent.reason)
                    stats.add_trade(intent, result, edge=edge, net_ev=net_ev, fair_prob=fair_prob)
            
            if loop % 10 == 0:
                print(f"[Progress] Loop {loop}/{args.loops} - Intents: {stats.total_intents}, Executed: {stats.total_executed}, Rejected: {stats.total_rejected}")

            sleep_time = 0.1 if args.fast else cfg.poll_seconds
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\n[Interrupted] Stopping simulation...")
    except Exception as e:
        print(f"\n[Error] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    stats.print_report()


if __name__ == "__main__":
    main()

