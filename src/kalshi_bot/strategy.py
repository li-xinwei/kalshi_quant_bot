from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from .kalshi.api import BestPrices
from .models import OrderIntent


@dataclass
class MarketSnapshot:
    ticker: str
    best: BestPrices


class Strategy:
    def generate(self, snaps: List[MarketSnapshot]) -> List[OrderIntent]:
        raise NotImplementedError


@dataclass
class FairValueConfig:
    fair_probs: Dict[str, float]  # ticker -> fair probability for YES
    edge_threshold: float         # in probability points, e.g. 0.04 == 4%


class SimpleFairValueStrategy(Strategy):
    """
    Starter strategy:
      - Reads fair probability for each ticker from config (FAIR_PROBS_JSON).
      - If fair > best_yes_ask + threshold: place a post-only bid for YES near ask (or slightly better).
      - If fair < best_yes_bid - threshold: place a post-only bid for NO (equivalently, selling YES).
    """
    def __init__(self, cfg: FairValueConfig, order_count: int = 5):
        self.cfg = cfg
        self.order_count = order_count

    def generate(self, snaps: List[MarketSnapshot]) -> List[OrderIntent]:
        intents: List[OrderIntent] = []
        for s in snaps:
            p_fair = self.cfg.fair_probs.get(s.ticker)
            if p_fair is None:
                continue  # no model, skip

            best = s.best
            # We'll compare to implied ask/bid in probability space.
            if best.yes_ask is not None:
                ask_p = best.yes_ask / 100.0
                if p_fair - ask_p >= self.cfg.edge_threshold:
                    # Buy YES; try to improve price by 1c if possible
                    px = max(1, best.yes_ask - 1)
                    intents.append(OrderIntent(
                        ticker=s.ticker, side="yes", action="buy",
                        count=self.order_count, price_cents=px,
                        reason=f"fair({p_fair:.2f}) > ask({ask_p:.2f}) + thr"
                    ))

            if best.yes_bid is not None:
                bid_p = best.yes_bid / 100.0
                if bid_p - p_fair >= self.cfg.edge_threshold:
                    # Market too expensive for YES; buy NO instead (post-only)
                    # best NO ask = 100 - best YES bid
                    if best.no_ask is None:
                        continue
                    px = max(1, best.no_ask - 1)
                    intents.append(OrderIntent(
                        ticker=s.ticker, side="no", action="buy",
                        count=self.order_count, price_cents=px,
                        reason=f"bid_yes({bid_p:.2f}) > fair({p_fair:.2f}) + thr"
                    ))
        return intents
