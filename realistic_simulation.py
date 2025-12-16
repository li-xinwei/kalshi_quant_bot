#!/usr/bin/env python3
"""
Realistic trading simulation based on actual Kalshi market data.
This script:
1. Fetches real market data from Kalshi
2. Analyzes market prices to determine fair probabilities
3. Simulates trading based on actual market conditions
"""
import argparse
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from kalshi_bot.config import BotConfig
from kalshi_bot.kalshi.auth import KalshiSigner
from kalshi_bot.kalshi.http import KalshiHTTPClient, RateLimiter
from kalshi_bot.kalshi.api import KalshiAPI
from kalshi_bot.strategy import MarketSnapshot, FeeAwareFairValueStrategy, FeeAwareConfig
from kalshi_bot.fair_prob import StaticFairProbProvider
from kalshi_bot.risk import RiskManager, RiskLimits
from kalshi_bot.execution import Executor, ExecutionResult
from kalshi_bot.models import OrderIntent


@dataclass
class MarketAnalysis:
    """Analysis of a real market"""
    ticker: str
    title: str
    yes_bid: Optional[int]
    yes_ask: Optional[int]
    no_bid: Optional[int]
    no_ask: Optional[int]
    mid_price: Optional[float]  # Mid price in probability (0-1)
    spread: Optional[float]  # Spread in probability
    volume_estimate: int = 0
    is_tradeable: bool = False
    
    def calculate_fair_prob(self) -> Optional[float]:
        """Calculate fair probability from market prices"""
        # Use mid price as fair probability estimate
        if self.mid_price is not None:
            return self.mid_price
        # Fallback: if we have bid or ask, use that
        if self.yes_bid is not None:
            return self.yes_bid / 100.0
        if self.yes_ask is not None:
            return self.yes_ask / 100.0
        return None


@dataclass
class RealisticSimulationStats:
    """Statistics for realistic simulation"""
    total_loops: int = 0
    markets_analyzed: int = 0
    tradeable_markets: int = 0
    total_intents: int = 0
    total_executed: int = 0
    total_rejected: int = 0
    
    # Market quality metrics
    avg_spread: float = 0.0
    markets_by_spread: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    # Price distribution
    price_distribution: Dict[int, int] = field(default_factory=lambda: defaultdict(int))
    
    # Edge statistics
    avg_edge: float = 0.0
    total_edge: float = 0.0
    positive_edge_trades: int = 0
    negative_edge_trades: int = 0
    
    # EV statistics
    total_net_ev: float = 0.0
    positive_ev_trades: int = 0
    
    # By ticker
    trades_by_ticker: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    def add_market(self, analysis: MarketAnalysis):
        """Add a market analysis"""
        self.markets_analyzed += 1
        if analysis.is_tradeable:
            self.tradeable_markets += 1
        if analysis.spread is not None:
            self.avg_spread = (self.avg_spread * (self.markets_analyzed - 1) + analysis.spread) / self.markets_analyzed
            if analysis.spread < 0.01:
                self.markets_by_spread["tight (<1%)"] += 1
            elif analysis.spread < 0.05:
                self.markets_by_spread["medium (1-5%)"] += 1
            else:
                self.markets_by_spread["wide (>5%)"] += 1
        
        if analysis.mid_price is not None:
            price_bucket = int(analysis.mid_price * 100)
            self.price_distribution[price_bucket] += 1
    
    def add_trade(self, intent: OrderIntent, result: ExecutionResult, edge: float, net_ev: float):
        """Add a trade to statistics"""
        self.total_intents += 1
        self.trades_by_ticker[intent.ticker] += 1
        
        self.total_edge += edge
        self.avg_edge = self.total_edge / self.total_intents
        
        if edge > 0:
            self.positive_edge_trades += 1
        else:
            self.negative_edge_trades += 1
        
        self.total_net_ev += net_ev
        if net_ev > 0:
            self.positive_ev_trades += 1
        
        if result.ok:
            self.total_executed += 1
        else:
            self.total_rejected += 1
    
    def print_report(self):
        """Print comprehensive statistics report"""
        print("\n" + "="*70)
        print("REALISTIC MARKET SIMULATION STATISTICS")
        print("="*70)
        
        print(f"\n📊 MARKET ANALYSIS:")
        print(f"  Markets Analyzed:      {self.markets_analyzed}")
        print(f"  Tradeable Markets:     {self.tradeable_markets} ({self.tradeable_markets/self.markets_analyzed*100:.1f}%)" if self.markets_analyzed > 0 else "  Tradeable Markets:     0")
        print(f"  Average Spread:        {self.avg_spread:.4f} ({self.avg_spread*100:.2f}%)")
        
        if self.markets_by_spread:
            print(f"\n  Spread Distribution:")
            for category, count in sorted(self.markets_by_spread.items()):
                print(f"    {category}: {count} markets")
        
        if self.price_distribution:
            print(f"\n  Price Distribution (mid prices):")
            sorted_prices = sorted(self.price_distribution.items())
            for price_bucket, count in sorted_prices[:10]:  # Show top 10
                print(f"    {price_bucket}%: {count} markets")
        
        print(f"\n📈 TRADING STATISTICS:")
        print(f"  Total Loops:           {self.total_loops}")
        print(f"  Total Trade Intents:   {self.total_intents}")
        print(f"  Executed:               {self.total_executed} ({self.total_executed/self.total_intents*100:.1f}%)" if self.total_intents > 0 else "  Executed:              0")
        print(f"  Rejected:               {self.total_rejected} ({self.total_rejected/self.total_intents*100:.1f}%)" if self.total_intents > 0 else "  Rejected:              0")
        
        if self.total_intents > 0:
            print(f"\n💰 EDGE ANALYSIS:")
            print(f"  Average Edge:           {self.avg_edge:.4f} ({self.avg_edge*100:.2f}%)")
            print(f"  Positive Edge Trades:  {self.positive_edge_trades} ({self.positive_edge_trades/self.total_intents*100:.1f}%)")
            print(f"  Negative Edge Trades:   {self.negative_edge_trades} ({self.negative_edge_trades/self.total_intents*100:.1f}%)")
            
            print(f"\n💵 EV ANALYSIS:")
            print(f"  Total Net EV:          ${self.total_net_ev:.4f}")
            print(f"  Positive EV Trades:     {self.positive_ev_trades} ({self.positive_ev_trades/self.total_intents*100:.1f}%)")
            print(f"  Average Net EV:        ${self.total_net_ev/self.total_intents:.4f}")
        
        if self.trades_by_ticker:
            print(f"\n📋 TRADES BY TICKER:")
            sorted_trades = sorted(self.trades_by_ticker.items(), key=lambda x: x[1], reverse=True)
            for ticker, count in sorted_trades[:10]:  # Top 10
                print(f"  {ticker}: {count} trades")
        
        print("\n" + "="*70)


def analyze_market(api: KalshiAPI, ticker: str) -> Optional[MarketAnalysis]:
    """Analyze a single market and return its characteristics"""
    try:
        market_info = api.get_market(ticker)
        market = market_info.get("market", market_info)
        title = market.get("title", "Unknown")
        
        ob = api.get_orderbook(ticker, depth=10)
        best = api.best_prices_from_orderbook(ob)
        
        # Calculate mid price
        mid_price = None
        spread = None
        
        if best.yes_bid is not None and best.yes_ask is not None:
            mid_price = (best.yes_bid + best.yes_ask) / 200.0  # Convert to 0-1
            spread = (best.yes_ask - best.yes_bid) / 100.0
        elif best.yes_bid is not None:
            mid_price = best.yes_bid / 100.0
        elif best.yes_ask is not None:
            mid_price = best.yes_ask / 100.0
        
        # Market is tradeable if it has both bid and ask (or at least one)
        is_tradeable = (best.yes_bid is not None or best.yes_ask is not None) and mid_price is not None
        
        return MarketAnalysis(
            ticker=ticker,
            title=title,
            yes_bid=best.yes_bid,
            yes_ask=best.yes_ask,
            no_bid=best.no_bid,
            no_ask=best.no_ask,
            mid_price=mid_price,
            spread=spread,
            is_tradeable=is_tradeable
        )
    except Exception as e:
        return None


def find_active_markets(api: KalshiAPI, limit: int = 50) -> List[str]:
    """Find active markets with orderbooks"""
    markets = api.get_markets(limit=limit, status="open")
    active_tickers = []
    
    for m in markets.get("markets", []):
        ticker = m.get("ticker")
        if not ticker:
            continue
        
        analysis = analyze_market(api, ticker)
        if analysis and analysis.is_tradeable:
            active_tickers.append(ticker)
            if len(active_tickers) >= limit:
                break
    
    return active_tickers


def extract_edge_from_reason(reason: str) -> Tuple[float, float]:
    """Extract edge and net_ev from reason string"""
    edge = 0.0
    net_ev = 0.0
    try:
        if "edge=" in reason:
            edge_str = reason.split("edge=")[1].split()[0]
            edge = float(edge_str)
        if "netEV=" in reason:
            ev_str = reason.split("netEV=")[1].split()[0]
            net_ev = float(ev_str)
    except:
        pass
    return edge, net_ev


def main():
    parser = argparse.ArgumentParser(description='Realistic trading simulation using real Kalshi market data')
    parser.add_argument('--loops', type=int, default=100, help='Number of loops to run')
    parser.add_argument('--markets', type=int, default=20, help='Number of markets to analyze')
    parser.add_argument('--paper', action='store_true', help='Paper trade mode')
    parser.add_argument('--fast', action='store_true', help='Fast mode: reduce sleep time')
    parser.add_argument('--edge-threshold', type=float, default=None, help='Override edge threshold')
    args = parser.parse_args()

    cfg = BotConfig.load()
    stats = RealisticSimulationStats()

    signer = KalshiSigner.from_pem_file(cfg.api_key_id, cfg.private_key_path)
    http = KalshiHTTPClient(
        host=cfg.host,
        signer=signer,
        read_rl=RateLimiter(per_second=15.0),
        write_rl=RateLimiter(per_second=8.0),
        timeout_s=10.0,
    )
    api = KalshiAPI(http)

    print("[Realistic Simulation] Finding active markets...")
    active_tickers = find_active_markets(api, limit=args.markets)
    
    if not active_tickers:
        print("[Error] No active markets found!")
        return
    
    print(f"[Realistic Simulation] Found {len(active_tickers)} active markets")
    
    # Analyze markets and determine fair probabilities from market prices
    market_fair_probs = {}
    market_analyses = {}
    
    print("[Realistic Simulation] Analyzing markets...")
    for ticker in active_tickers:
        analysis = analyze_market(api, ticker)
        if analysis:
            market_analyses[ticker] = analysis
            stats.add_market(analysis)
            fair_prob = analysis.calculate_fair_prob()
            if fair_prob is not None:
                # Use market mid price as fair probability, but add a small random adjustment
                # to simulate having a different view (this creates trading opportunities)
                import random
                adjustment = random.uniform(-0.02, 0.02)  # ±2% adjustment
                market_fair_probs[ticker] = max(0.01, min(0.99, fair_prob + adjustment))
    
    print(f"[Realistic Simulation] Analyzed {len(market_analyses)} markets")
    print(f"[Realistic Simulation] Tradeable markets: {stats.tradeable_markets}")
    
    if not market_fair_probs:
        print("[Error] No markets with valid fair probabilities!")
        return
    
    # Use analyzed markets as tickers
    cfg_tickers = list(market_fair_probs.keys())[:min(10, len(market_fair_probs))]  # Use up to 10 markets
    
    # Create strategy with market-based fair probabilities
    provider = StaticFairProbProvider(market_fair_probs)
    
    edge_threshold = args.edge_threshold if args.edge_threshold is not None else cfg.edge_threshold
    
    strat = FeeAwareFairValueStrategy(
        FeeAwareConfig(
            edge_threshold=edge_threshold,
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

    print(f"\n[Realistic Simulation] Starting simulation")
    print(f"[Realistic Simulation] Loops: {args.loops}")
    print(f"[Realistic Simulation] Markets: {len(cfg_tickers)}")
    print(f"[Realistic Simulation] Edge threshold: {edge_threshold}")
    print(f"[Realistic Simulation] Paper mode: {args.paper}")
    print()

    try:
        for loop in range(1, args.loops + 1):
            stats.total_loops = loop
            
            snaps: List[MarketSnapshot] = []
            for t in cfg_tickers:
                try:
                    ob = api.get_orderbook(t, depth=10)
                    best = api.best_prices_from_orderbook(ob)
                    snaps.append(MarketSnapshot(ticker=t, best=best))
                except Exception as e:
                    if loop % 20 == 0:
                        print(f"[data] {t}: error - {e}")

            intents = strat.generate(snaps)
            
            if intents:
                results = exe.execute(intents)
                for intent, result in zip(intents, results):
                    edge, net_ev = extract_edge_from_reason(intent.reason)
                    stats.add_trade(intent, result, edge=edge, net_ev=net_ev)
            
            if loop % 20 == 0:
                print(f"[Progress] Loop {loop}/{args.loops} - Intents: {stats.total_intents}, Executed: {stats.total_executed}, Markets: {stats.tradeable_markets}")

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

