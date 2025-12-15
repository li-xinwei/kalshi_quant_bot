from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .http import KalshiHTTPClient


def _best_bid(bids: List[List[int]]) -> Optional[int]:
    if not bids:
        return None
    # arrays sorted ascending by price; best bid is last element
    return int(bids[-1][0])


@dataclass(frozen=True)
class BestPrices:
    yes_bid: Optional[int]
    yes_ask: Optional[int]
    no_bid: Optional[int]
    no_ask: Optional[int]

    @property
    def mid_yes(self) -> Optional[float]:
        if self.yes_bid is None or self.yes_ask is None:
            return None
        return (self.yes_bid + self.yes_ask) / 2.0 / 100.0


class KalshiAPI:
    def __init__(self, http: KalshiHTTPClient):
        self.http = http

    # ---------- Public market data ----------
    def get_markets(self, limit: int = 100, status: str = "open", cursor: Optional[str] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {"limit": limit, "status": status}
        if cursor:
            params["cursor"] = cursor
        return self.http.get("/markets", params=params)

    def get_market(self, ticker: str) -> Dict[str, Any]:
        return self.http.get(f"/markets/{ticker}")

    def get_orderbook(self, ticker: str, depth: int = 10) -> Dict[str, Any]:
        return self.http.get(f"/markets/{ticker}/orderbook", params={"depth": depth})

    def get_milestones(
        self,
        *,
        limit: int = 100,
        minimum_start_date: Optional[str] = None,
        category: Optional[str] = None,
        competition: Optional[str] = None,
        source_id: Optional[str] = None,
        type: Optional[str] = None,
        related_event_ticker: Optional[str] = None,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"limit": int(limit)}
        if minimum_start_date:
            params["minimum_start_date"] = minimum_start_date
        if category:
            params["category"] = category
        if competition:
            params["competition"] = competition
        if source_id:
            params["source_id"] = source_id
        if type:
            params["type"] = type
        if related_event_ticker:
            params["related_event_ticker"] = related_event_ticker
        if cursor:
            params["cursor"] = cursor
        return self.http.get("/milestones", params=params)

    def get_milestone(self, milestone_id: str) -> Dict[str, Any]:
        return self.http.get(f"/milestones/{milestone_id}")

    def get_live_data(self, *, live_type: str, milestone_id: str) -> Dict[str, Any]:
        return self.http.get(f"/live_data/{live_type}/milestone/{milestone_id}")

    def get_multiple_live_data(self, *, milestone_ids: List[str]) -> Dict[str, Any]:
        # GET /live_data/batch?milestone_ids=...
        return self.http.get("/live_data/batch", params={"milestone_ids": list(milestone_ids)})

    def best_prices_from_orderbook(self, orderbook_json: Dict[str, Any]) -> BestPrices:
        ob = orderbook_json["orderbook"]
        yes_bid = _best_bid(ob.get("yes", []))
        no_bid = _best_bid(ob.get("no", []))

        # Kalshi reciprocal relationship:
        # best YES ask = 100 - best NO bid
        # best NO ask  = 100 - best YES bid
        yes_ask = (100 - no_bid) if no_bid is not None else None
        no_ask = (100 - yes_bid) if yes_bid is not None else None

        return BestPrices(yes_bid=yes_bid, yes_ask=yes_ask, no_bid=no_bid, no_ask=no_ask)

    # ---------- Authenticated portfolio / orders ----------
    def get_balance(self) -> Dict[str, Any]:
        return self.http.get("/portfolio/balance")

    def get_positions(self, ticker: Optional[str] = None, limit: int = 200) -> Dict[str, Any]:
        params: Dict[str, Any] = {"limit": limit}
        if ticker:
            params["ticker"] = ticker
        return self.http.get("/portfolio/positions", params=params)

    def get_orders(self, status: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
        params: Dict[str, Any] = {"limit": limit}
        if status:
            params["status"] = status
        return self.http.get("/portfolio/orders", params=params)

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        return self.http.delete(f"/portfolio/orders/{order_id}")

    def create_limit_order(
        self,
        ticker: str,
        side: str,   # "yes" or "no"
        action: str, # "buy" or "sell"
        count: int,
        price_cents: int,
        client_order_id: Optional[str] = None,
        post_only: bool = True,
        reduce_only: bool = False,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "ticker": ticker,
            "side": side,
            "action": action,
            "count": int(count),
            "type": "limit",
            "post_only": bool(post_only),
            "reduce_only": bool(reduce_only),
        }
        if client_order_id:
            body["client_order_id"] = client_order_id

        # For limit orders: supply yes_price or no_price depending on side.
        if side == "yes":
            body["yes_price"] = int(price_cents)
        elif side == "no":
            body["no_price"] = int(price_cents)
        else:
            raise ValueError("side must be 'yes' or 'no'")

        return self.http.post("/portfolio/orders", json_body=body)
