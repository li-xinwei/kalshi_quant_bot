from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Literal

Side = Literal["yes", "no"]
Action = Literal["buy", "sell"]

@dataclass(frozen=True)
class OrderIntent:
    ticker: str
    side: Side
    action: Action
    count: int
    price_cents: int
    reason: str = ""
    client_order_id: Optional[str] = None
