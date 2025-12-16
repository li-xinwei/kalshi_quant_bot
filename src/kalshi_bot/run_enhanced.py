"""
Enhanced trading bot with all features: logging, database, monitoring, etc.
"""
from __future__ import annotations

import argparse
import signal
import sys
import time
from pathlib import Path
from typing import List

# Add src to path if running as script
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

from kalshi_bot.config import BotConfig
from kalshi_bot.kalshi.auth import KalshiSigner
from kalshi_bot.kalshi.http import KalshiHTTPClient, RateLimiter
from kalshi_bot.kalshi.api import KalshiAPI
from kalshi_bot.strategy import MarketSnapshot, FeeAwareFairValueStrategy, FeeAwareConfig
from kalshi_bot.fair_prob import StaticFairProbProvider, LiveDataWinProbProvider
from kalshi_bot.risk import RiskManager, RiskLimits
from kalshi_bot.execution import Executor
from kalshi_bot.database import Database
from kalshi_bot.monitoring import MonitoringSystem
from kalshi_bot.order_manager import OrderManager
from kalshi_bot.logging_config import setup_logging, get_logger


def main():
    parser = argparse.ArgumentParser(description="Enhanced Kalshi trading bot")
    parser.add_argument("--paper", action="store_true", help="Paper trade mode")
    parser.add_argument("--max-loops", type=int, default=None, help="Maximum number of loops")
    parser.add_argument("--timeout", type=int, default=None, help="Maximum seconds to run")
    parser.add_argument("--db-path", type=str, default="kalshi_bot.db", help="Database path")
    parser.add_argument("--log-dir", type=str, default="logs", help="Log directory")
    parser.add_argument("--log-level", type=str, default="INFO", help="Log level")
    args = parser.parse_args()

    # Setup logging
    logger = setup_logging(
        log_dir=args.log_dir,
        log_level=args.log_level,
        log_to_file=True,
        log_to_console=True,
    )
    logger.info("Starting enhanced Kalshi trading bot")

    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info("Received interrupt signal, shutting down gracefully...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    if args.timeout:
        def timeout_handler(signum, frame):
            logger.info(f"Timeout reached ({args.timeout}s), stopping...")
            sys.exit(0)
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(args.timeout)

    # Load configuration
    cfg = BotConfig.load()
    logger.info(f"Configuration loaded: env={cfg.env}, tickers={cfg.tickers}")

    # Initialize database
    db = Database(db_path=args.db_path)
    logger.info(f"Database initialized: {args.db_path}")

    # Initialize monitoring
    monitoring = MonitoringSystem(db)
    logger.info("Monitoring system initialized")

    # Initialize API
    signer = KalshiSigner.from_pem_file(cfg.api_key_id, cfg.private_key_path)
    http = KalshiHTTPClient(
        host=cfg.host,
        signer=signer,
        read_rl=RateLimiter(per_second=15.0),
        write_rl=RateLimiter(per_second=8.0),
        timeout_s=10.0,
    )
    api = KalshiAPI(http)

    # Initialize order manager
    order_manager = OrderManager(api, db)

    # Initialize strategy
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

    # Initialize risk manager and executor
    risk = RiskManager(api, RiskLimits(cfg.max_order_count, cfg.max_position_per_ticker))
    exe = Executor(api, risk, paper=args.paper, db=db, monitoring=monitoring)

    logger.info(f"Bot initialized: paper={args.paper}, tickers={cfg.tickers}")

    # Health check
    health = monitoring.check_health()
    logger.info(f"Health check: {health['status']}")

    loop_count = 0
    try:
        while True:
            loop_count += 1
            if args.max_loops and loop_count > args.max_loops:
                logger.info(f"Reached maximum loops ({args.max_loops}), stopping...")
                break

            # Record loop start time
            loop_start = time.time()

            # Fetch market data
            snaps: List[MarketSnapshot] = []
            for t in cfg.tickers:
                try:
                    ob = api.get_orderbook(t, depth=10)
                    best = api.best_prices_from_orderbook(ob)
                    snaps.append(MarketSnapshot(ticker=t, best=best))
                    
                    # Save market snapshot for backtesting
                    db.save_market_snapshot(
                        ticker=t,
                        yes_bid=best.yes_bid,
                        yes_ask=best.yes_ask,
                        no_bid=best.no_bid,
                        no_ask=best.no_ask,
                    )
                except Exception as e:
                    logger.error(f"Error fetching orderbook for {t}: {e}")
                    monitoring.send_alert("error", f"Failed to fetch orderbook: {t}", {"ticker": t, "error": str(e)})

            # Generate trading signals
            intents = strat.generate(snaps)
            
            if intents:
                logger.info(f"Generated {len(intents)} trade intents")
                for it in intents:
                    logger.debug(f"Intent: {it.ticker} {it.action} {it.side} {it.count}@{it.price_cents}c - {it.reason}")

                # Execute orders
                results = exe.execute(intents)
                for r in results:
                    status = "OK" if r.ok else "FAIL"
                    logger.info(f"Execution {status}: {r.intent.ticker} {r.intent.action} {r.intent.side} -> {r.detail}")
            else:
                logger.debug("No trading opportunities found")

            # Record loop latency
            loop_latency = (time.time() - loop_start) * 1000
            monitoring.record_metric("loop_latency_ms", loop_latency)

            # Periodic health check (every 10 loops)
            if loop_count % 10 == 0:
                health = monitoring.check_health()
                logger.debug(f"Health check: {health['status']}")

            # Sync orders periodically (every 50 loops)
            if loop_count % 50 == 0 and not args.paper:
                logger.info("Syncing orders from API...")
                sync_stats = order_manager.sync_all_orders()
                logger.info(f"Synced {sync_stats['synced']} orders")

            time.sleep(cfg.poll_seconds)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        monitoring.send_alert("critical", f"Fatal error: {e}", {"error": str(e)})
        sys.exit(1)
    finally:
        logger.info("Shutting down...")
        db.close()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    main()

