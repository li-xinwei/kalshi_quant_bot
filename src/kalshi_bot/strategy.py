from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from .kalshi.api import BestPrices
from .models import OrderIntent
from .fees import net_ev_per_contract
from .fair_prob import FairProbProvider


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


@dataclass
class FeeAwareConfig:
    edge_threshold: float
    fee_kind: str  # "taker" | "maker" | "none"
    taker_fee_rate: float
    maker_fee_rate: float
    min_net_ev_per_contract: float
    post_only: bool


class FeeAwareFairValueStrategy(Strategy):
    """Fair-value strategy that is aware of fees + can use a dynamic fair-prob provider.

    This is the "strategy #2" foundation:
      - You supply an independent probability estimate (FairProbProvider).
      - We only trade if edge remains positive after a conservative fee estimate.

    You can upgrade the provider to a proper in-play model for sports.
    """

    def __init__(self, cfg: FeeAwareConfig, provider: FairProbProvider, order_count: int = 5):
        self.cfg = cfg
        self.provider = provider
        self.order_count = order_count

    def _target_px(self, ask_cents: int) -> int:
        # Maker-style: try to improve by 1c so we don't cross.
        return max(1, ask_cents - 1) if self.cfg.post_only else ask_cents

    def generate(self, snaps: List[MarketSnapshot]) -> List[OrderIntent]:
        intents: List[OrderIntent] = []
        for s in snaps:
            p_fair = self.provider.get_fair_prob_yes(s.ticker)
            if p_fair is None:
                continue

            best = s.best

            # Candidate 1: BUY YES
            if best.yes_ask is not None:
                px = self._target_px(best.yes_ask)
                edge = float(p_fair) - (px / 100.0)
                net = net_ev_per_contract(
                    fair_prob_yes=float(p_fair),
                    price_cents=px,
                    fee_kind=self.cfg.fee_kind,
                    taker_rate=self.cfg.taker_fee_rate,
                    maker_rate=self.cfg.maker_fee_rate,
                )
                if edge >= self.cfg.edge_threshold and net >= self.cfg.min_net_ev_per_contract:
                    intents.append(
                        OrderIntent(
                            ticker=s.ticker,
                            side="yes",
                            action="buy",
                            count=self.order_count,
                            price_cents=px,
                            post_only=self.cfg.post_only,
                            reason=f"YES netEV={net:.4f} edge={edge:.3f} fair={p_fair:.3f}"
                        )
                    )
                    continue  # don't place both sides in same tick

            # Candidate 2: BUY NO
            if best.no_ask is not None:
                px = self._target_px(best.no_ask)
                p_no = 1.0 - float(p_fair)
                edge = p_no - (px / 100.0)
                net = net_ev_per_contract(
                    fair_prob_yes=p_no,
                    price_cents=px,
                    fee_kind=self.cfg.fee_kind,
                    taker_rate=self.cfg.taker_fee_rate,
                    maker_rate=self.cfg.maker_fee_rate,
                )
                if edge >= self.cfg.edge_threshold and net >= self.cfg.min_net_ev_per_contract:
                    intents.append(
                        OrderIntent(
                            ticker=s.ticker,
                            side="no",
                            action="buy",
                            count=self.order_count,
                            price_cents=px,
                            post_only=self.cfg.post_only,
                            reason=f"NO netEV={net:.4f} edge={edge:.3f} fairNO={p_no:.3f}"
                        )
                    )

        return intents
