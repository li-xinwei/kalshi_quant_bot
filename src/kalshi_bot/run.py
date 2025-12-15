from __future__ import annotations

import argparse
import time
from typing import List

from .config import BotConfig
from .kalshi.auth import KalshiSigner
from .kalshi.http import KalshiHTTPClient, RateLimiter
from .kalshi.api import KalshiAPI
from .strategy import MarketSnapshot, FeeAwareFairValueStrategy, FeeAwareConfig
from .fair_prob import StaticFairProbProvider, LiveDataWinProbProvider
from .risk import RiskManager, RiskLimits
from .execution import Executor


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper", action="store_true", help="Paper trade (no orders submitted)")
    args = parser.parse_args()

    cfg = BotConfig.load()

    signer = KalshiSigner.from_pem_file(cfg.api_key_id, cfg.private_key_path)

    # Start with Basic tier defaults; tune based on your API tier.
    # Kalshi publishes per-second limits by tier.
    http = KalshiHTTPClient(
        host=cfg.host,
        signer=signer,
        read_rl=RateLimiter(per_second=15.0),
        write_rl=RateLimiter(per_second=8.0),
        timeout_s=10.0,
    )
    api = KalshiAPI(http)

    # Strategy #2 foundation: independent fair-prob model vs market price (fee-aware)
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

    while True:
        snaps: List[MarketSnapshot] = []
        for t in cfg.tickers:
            try:
                ob = api.get_orderbook(t, depth=10)
                best = api.best_prices_from_orderbook(ob)
                snaps.append(MarketSnapshot(ticker=t, best=best))
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

        time.sleep(cfg.poll_seconds)


if __name__ == "__main__":
    main()
