from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from .kalshi.api import KalshiAPI


class FairProbProvider:
    """Provides a fair probability for YES for a given market ticker."""

    def get_fair_prob_yes(self, ticker: str) -> Optional[float]:
        raise NotImplementedError


@dataclass
class StaticFairProbProvider(FairProbProvider):
    fair_probs_yes: Dict[str, float]

    def get_fair_prob_yes(self, ticker: str) -> Optional[float]:
        p = self.fair_probs_yes.get(ticker)
        if p is None:
            return None
        return max(0.0, min(1.0, float(p)))


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _logit(p: float) -> float:
    p = max(1e-6, min(1.0 - 1e-6, p))
    return math.log(p / (1.0 - p))


def _parse_clock_to_seconds(clock: object) -> Optional[int]:
    """Try to parse a clock value into seconds.

    Handles common formats like:
      - "12:34"
      - 754 (already seconds)
      - {"minutes": 12, "seconds": 34}
    """
    if clock is None:
        return None
    if isinstance(clock, (int, float)):
        return int(clock)
    if isinstance(clock, dict):
        m = clock.get("minutes")
        s = clock.get("seconds")
        if isinstance(m, (int, float)) and isinstance(s, (int, float)):
            return int(m) * 60 + int(s)
    if isinstance(clock, str):
        parts = clock.strip().split(":")
        if len(parts) == 2 and all(p.isdigit() for p in parts):
            return int(parts[0]) * 60 + int(parts[1])
    return None


def _extract_team_scores(details: dict, yes_hint: Optional[str], no_hint: Optional[str]) -> Tuple[Optional[int], Optional[int]]:
    """Best-effort extraction of YES-side and NO-side scores from live-data details.

    Because the exact schema depends on the sport/source, we try multiple patterns.
    """
    # Direct keys
    for ys, ns in [
        ("yes_score", "no_score"),
        ("yesScore", "noScore"),
        ("team_yes_score", "team_no_score"),
    ]:
        if ys in details and ns in details:
            try:
                return int(details[ys]), int(details[ns])
            except Exception:
                pass

    # Home/Away keys (we'll map later via name matching if possible)
    home_score = None
    away_score = None
    for hk, ak in [
        ("home_score", "away_score"),
        ("homeScore", "awayScore"),
        ("homePoints", "awayPoints"),
        ("home", "away"),  # sometimes nested
    ]:
        if hk in details and ak in details:
            try:
                if isinstance(details[hk], dict) and "score" in details[hk]:
                    home_score = int(details[hk]["score"])
                else:
                    home_score = int(details[hk])

                if isinstance(details[ak], dict) and "score" in details[ak]:
                    away_score = int(details[ak]["score"])
                else:
                    away_score = int(details[ak])
                break
            except Exception:
                pass

    # If we have home/away scores, attempt to map using team name hints
    if home_score is not None and away_score is not None:
        home_name = (
            details.get("home_team")
            or details.get("homeTeam")
            or (details.get("home") or {}).get("name") if isinstance(details.get("home"), dict) else None
        )
        away_name = (
            details.get("away_team")
            or details.get("awayTeam")
            or (details.get("away") or {}).get("name") if isinstance(details.get("away"), dict) else None
        )

        def _match(hint: Optional[str], name: Optional[str]) -> bool:
            if not hint or not name:
                return False
            return hint.lower() in name.lower() or name.lower() in hint.lower()

        if _match(yes_hint, home_name) or _match(yes_hint, details.get("home")):
            return home_score, away_score
        if _match(yes_hint, away_name) or _match(yes_hint, details.get("away")):
            return away_score, home_score

    return None, None


@dataclass
class LiveDataWinProbProvider(FairProbProvider):
    """A pragmatic *in-play* probability provider built on Kalshi's milestones + live-data.

    Design goal: give you a clean place to plug a real model.

    How it works (high-level):
    - Use pregame fair prob as a prior (from fair_probs_yes).
    - Fetch the market -> event_ticker, then find the associated milestone (via get_milestones).
    - Pull live data for that milestone.
    - Convert score/time into a win-prob adjustment on the logit scale.

    IMPORTANT: live-data schemas vary by sport/provider. If we can't parse state safely,
    we fall back to the pregame prior.
    """

    api: KalshiAPI
    fair_probs_yes: Dict[str, float]
    # Model coefficients (you will tune these with historical backtests)
    coef_score_diff: float = 0.12
    coef_time_left_min: float = -0.03
    coef_prior: float = 1.0

    _cache: Dict[str, Tuple[str, str]] = None  # ticker -> (milestone_id, live_type)
    _name_hints: Dict[str, Tuple[Optional[str], Optional[str]]] = None  # ticker -> (yes_hint, no_hint)

    def __post_init__(self):
        self._cache = {}
        self._name_hints = {}

    def _ensure_milestone(self, ticker: str) -> Optional[Tuple[str, str]]:
        if ticker in self._cache:
            return self._cache[ticker]
        try:
            mkt = self.api.get_market(ticker)
            market = mkt.get("market", mkt)  # defensive: some wrappers nest
            event_ticker = market.get("event_ticker")
            yes_hint = market.get("yes_sub_title") or market.get("subtitle") or market.get("title")
            no_hint = market.get("no_sub_title") or market.get("subtitle")
            self._name_hints[ticker] = (yes_hint, no_hint)
            if not event_ticker:
                return None

            # Search milestones related to this event ticker
            resp = self.api.get_milestones(limit=50, related_event_ticker=event_ticker)
            milestones = resp.get("milestones", [])
            if not milestones:
                return None
            # Prefer milestones where this event is primary, else take first.
            chosen = None
            for ms in milestones:
                if event_ticker in (ms.get("primary_event_tickers") or []):
                    chosen = ms
                    break
            if chosen is None:
                chosen = milestones[0]
            ms_id = chosen.get("id")
            live_type = chosen.get("type") or chosen.get("category") or "sports"
            if not ms_id:
                return None
            self._cache[ticker] = (ms_id, str(live_type))
            return self._cache[ticker]
        except Exception:
            return None

    def get_fair_prob_yes(self, ticker: str) -> Optional[float]:
        prior = self.fair_probs_yes.get(ticker)
        if prior is None:
            return None

        ms = self._ensure_milestone(ticker)
        if not ms:
            return max(0.0, min(1.0, float(prior)))

        ms_id, live_type = ms
        try:
            live = self.api.get_live_data(live_type=live_type, milestone_id=ms_id)
            data = live.get("live_data", live)
            details = data.get("details") or {}
            if not isinstance(details, dict):
                return max(0.0, min(1.0, float(prior)))

            # Best-effort parse
            yes_hint, no_hint = self._name_hints.get(ticker, (None, None))
            score_yes, score_no = _extract_team_scores(details, yes_hint=yes_hint, no_hint=no_hint)
            if score_yes is None or score_no is None:
                return max(0.0, min(1.0, float(prior)))

            # time left: try multiple keys
            t_left = (
                _parse_clock_to_seconds(details.get("time_remaining"))
                or _parse_clock_to_seconds(details.get("clock"))
                or _parse_clock_to_seconds(details.get("timeRemaining"))
                or _parse_clock_to_seconds((details.get("game") or {}).get("clock") if isinstance(details.get("game"), dict) else None)
            )

            diff = float(score_yes - score_no)
            t_min = float(t_left) / 60.0 if isinstance(t_left, int) else 0.0

            # Simple in-play logit model
            x = (
                self.coef_prior * _logit(float(prior))
                + self.coef_score_diff * diff
                + self.coef_time_left_min * t_min
            )
            p = _sigmoid(x)
            return max(0.0, min(1.0, float(p)))
        except Exception:
            return max(0.0, min(1.0, float(prior)))
