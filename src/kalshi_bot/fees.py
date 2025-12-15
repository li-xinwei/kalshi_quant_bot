from __future__ import annotations

import math


def _round_up_to_cent(dollars: float) -> float:
    """Round up to the next $0.01 (Kalshi fee schedule says 'round up')."""
    # Avoid floating-point edge cases (e.g., 0.01000000002)
    return math.ceil((dollars - 1e-12) * 100.0) / 100.0


def kalshi_fee_dollars(
    *,
    price_cents: int,
    count: int,
    kind: str = "taker",
    taker_rate: float = 0.07,
    maker_rate: float = 0.0175,
) -> float:
    """Estimate Kalshi trading fees (USD) for a single fill.

    Per Kalshi fee schedule, the general formula is:
      fees = round_up(rate * C * P * (1-P))
    where P is contract price in dollars and C is # of contracts.

    Notes:
    - Some products have different rates (you can override rates via args).
    - Maker fees apply only to certain markets; you must decide when to assume maker vs taker.
    """
    if count <= 0:
        return 0.0
    P = max(0.0, min(0.99, price_cents / 100.0))
    rate = taker_rate if kind == "taker" else maker_rate if kind == "maker" else 0.0
    return _round_up_to_cent(rate * float(count) * P * (1.0 - P))


def net_ev_per_contract(
    *,
    fair_prob_yes: float,
    price_cents: int,
    fee_kind: str,
    taker_rate: float,
    maker_rate: float,
) -> float:
    """Expected value per contract (in USD) if you BUY YES at price_cents and hold to settlement."""
    Pm = price_cents / 100.0
    gross = float(fair_prob_yes) - Pm
    fees = kalshi_fee_dollars(
        price_cents=price_cents,
        count=1,
        kind=fee_kind,
        taker_rate=taker_rate,
        maker_rate=maker_rate,
    )
    return gross - fees
