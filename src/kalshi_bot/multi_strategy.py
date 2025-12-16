"""
Multi-strategy support for running multiple strategies simultaneously.
"""
from typing import List, Dict, Optional
from dataclasses import dataclass

from .strategy import Strategy, MarketSnapshot
from .models import OrderIntent
from .logging_config import get_logger

logger = get_logger("multi_strategy")


@dataclass
class StrategyConfig:
    """Configuration for a strategy"""
    name: str
    strategy: Strategy
    enabled: bool = True
    weight: float = 1.0  # Weight for combining signals
    max_order_count: int = 5


class MultiStrategyManager:
    """Manages multiple strategies and combines their signals"""
    
    def __init__(self, strategies: List[StrategyConfig]):
        self.strategies = strategies
        self.enabled_strategies = [s for s in strategies if s.enabled]
    
    def generate(self, snaps: List[MarketSnapshot]) -> List[OrderIntent]:
        """
        Generate orders from all enabled strategies.
        Combines signals from multiple strategies.
        """
        all_intents: List[OrderIntent] = []
        
        for strategy_config in self.enabled_strategies:
            try:
                intents = strategy_config.strategy.generate(snaps)
                
                # Apply strategy-specific limits
                intents = intents[:strategy_config.max_order_count]
                
                # Tag intents with strategy name
                for intent in intents:
                    intent.reason = f"[{strategy_config.name}] {intent.reason}"
                
                all_intents.extend(intents)
                logger.debug(f"Strategy {strategy_config.name} generated {len(intents)} intents")
                
            except Exception as e:
                logger.error(f"Strategy {strategy_config.name} failed: {e}")
        
        # Deduplicate intents (same ticker, side, action, price)
        deduplicated = self._deduplicate_intents(all_intents)
        
        logger.info(f"Multi-strategy generated {len(deduplicated)} total intents from {len(self.enabled_strategies)} strategies")
        return deduplicated
    
    def _deduplicate_intents(self, intents: List[OrderIntent]) -> List[OrderIntent]:
        """Remove duplicate intents"""
        seen = set()
        unique = []
        
        for intent in intents:
            key = (intent.ticker, intent.side, intent.action, intent.price_cents)
            if key not in seen:
                seen.add(key)
                unique.append(intent)
            else:
                # Merge counts if duplicate
                for existing in unique:
                    if (existing.ticker == intent.ticker and
                        existing.side == intent.side and
                        existing.action == intent.action and
                        existing.price_cents == intent.price_cents):
                        existing.count += intent.count
                        break
        
        return unique
    
    def enable_strategy(self, name: str):
        """Enable a strategy"""
        for strategy_config in self.strategies:
            if strategy_config.name == name:
                strategy_config.enabled = True
                logger.info(f"Enabled strategy: {name}")
                return
        logger.warning(f"Strategy not found: {name}")
    
    def disable_strategy(self, name: str):
        """Disable a strategy"""
        for strategy_config in self.strategies:
            if strategy_config.name == name:
                strategy_config.enabled = False
                logger.info(f"Disabled strategy: {name}")
                return
        logger.warning(f"Strategy not found: {name}")
    
    def get_strategy_status(self) -> Dict[str, bool]:
        """Get status of all strategies"""
        return {s.name: s.enabled for s in self.strategies}

