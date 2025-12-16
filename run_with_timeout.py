#!/usr/bin/env python3
"""
Wrapper script to run kalshi_bot with a timeout limit.
Usage: python run_with_timeout.py [--paper] [--max-loops N] [--timeout SECONDS]
"""
import argparse
import signal
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from kalshi_bot.run import main as bot_main
from kalshi_bot.config import BotConfig
from kalshi_bot.kalshi.auth import KalshiSigner
from kalshi_bot.kalshi.http import KalshiHTTPClient, RateLimiter
from kalshi_bot.kalshi.api import KalshiAPI
from kalshi_bot.strategy import MarketSnapshot, FeeAwareFairValueStrategy, FeeAwareConfig
from kalshi_bot.fair_prob import StaticFairProbProvider, LiveDataWinProbProvider
from kalshi_bot.risk import RiskManager, RiskLimits
from kalshi_bot.execution import Executor


def timeout_handler(signum, frame):
    print('\n[Timeout] Maximum time reached. Stopping...')
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description='Run Kalshi bot with timeout/loop limits')
    parser.add_argument('--paper', action='store_true', help='Paper trade mode')
    parser.add_argument('--max-loops', type=int, default=None, help='Maximum number of loops to run')
    parser.add_argument('--timeout', type=int, default=None, help='Maximum seconds to run')
    args = parser.parse_args()

    cfg = BotConfig.load()

    if args.timeout:
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(args.timeout)
        print(f'[Info] Will stop after {args.timeout} seconds')

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

    print(f"[kalshi-bot] env={cfg.env} host={cfg.host} paper={args.paper}")
    print(f"[kalshi-bot] tickers={cfg.tickers}")
    print(f"[kalshi-bot] fee_kind={cfg.fee_kind} post_only={cfg.post_only} min_net_ev=${cfg.min_net_ev_per_contract:.4f}")
    print(f"[kalshi-bot] use_live_data={cfg.use_live_data}")
    if cfg.fair_probs:
        print(f"[kalshi-bot] fair_probs={cfg.fair_probs}")
    else:
        print(f"[kalshi-bot] WARNING: No fair_probs configured! Strategy won't generate trades.")
    print()

    loop_count = 0
    try:
        while True:
            loop_count += 1
            if args.max_loops and loop_count > args.max_loops:
                print(f'\n[Info] Reached maximum loops ({args.max_loops}). Stopping...')
                break

            snaps = []
            for t in cfg.tickers:
                try:
                    ob = api.get_orderbook(t, depth=10)
                    best = api.best_prices_from_orderbook(ob)
                    snaps.append(MarketSnapshot(ticker=t, best=best))
                    print(f"[data] {t}: YES bid={best.yes_bid}c ask={best.yes_ask}c NO bid={best.no_bid}c ask={best.no_ask}c")
                except Exception as e:
                    print(f"[data] {t}: error fetching orderbook: {e}")

            intents = strat.generate(snaps)
            if intents:
                print(f"[strategy] intents={len(intents)}")
                for it in intents:
                    print(f"  - {it.ticker} {it.action} {it.side} {it.count}@{it.price_cents}c :: {it.reason}")

                results = exe.execute(intents)
                for r in results:
                    status = "OK" if r.ok else "FAIL"
                    print(f"[exec] {status} {r.intent.ticker} {r.intent.action} {r.intent.side} {r.intent.count}@{r.intent.price_cents}c -> {r.detail}")
            else:
                print("[strategy] no trades")

            print(f"[loop {loop_count}] Sleeping {cfg.poll_seconds}s...\n")
            time.sleep(cfg.poll_seconds)

    except KeyboardInterrupt:
        print('\n[Interrupted] Stopping...')
    except Exception as e:
        print(f'\n[Error] {type(e).__name__}: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

