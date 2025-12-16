"""
Unit tests for strategy module.
"""
import unittest
from kalshi_bot.strategy import SimpleFairValueStrategy, FairValueConfig, MarketSnapshot
from kalshi_bot.kalshi.api import BestPrices
from kalshi_bot.fair_prob import StaticFairProbProvider


class TestSimpleFairValueStrategy(unittest.TestCase):
    """Test SimpleFairValueStrategy"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = FairValueConfig(
            fair_probs={"TEST-TICKER": 0.5},
            edge_threshold=0.05,
        )
        self.strategy = SimpleFairValueStrategy(self.config, order_count=5)
    
    def test_generate_buy_yes(self):
        """Test generating buy YES order when fair > ask + threshold"""
        best = BestPrices(yes_bid=40, yes_ask=45, no_bid=55, no_ask=60)
        snap = MarketSnapshot(ticker="TEST-TICKER", best=best)
        
        intents = self.strategy.generate([snap])
        
        self.assertEqual(len(intents), 1)
        self.assertEqual(intents[0].side, "yes")
        self.assertEqual(intents[0].action, "buy")
        self.assertEqual(intents[0].ticker, "TEST-TICKER")
    
    def test_generate_buy_no(self):
        """Test generating buy NO order when bid > fair + threshold"""
        best = BestPrices(yes_bid=60, yes_ask=65, no_bid=35, no_ask=40)
        snap = MarketSnapshot(ticker="TEST-TICKER", best=best)
        
        intents = self.strategy.generate([snap])
        
        self.assertEqual(len(intents), 1)
        self.assertEqual(intents[0].side, "no")
        self.assertEqual(intents[0].action, "buy")
    
    def test_no_trade_when_no_edge(self):
        """Test no trade when edge is below threshold"""
        best = BestPrices(yes_bid=48, yes_ask=52, no_bid=48, no_ask=52)
        snap = MarketSnapshot(ticker="TEST-TICKER", best=best)
        
        intents = self.strategy.generate([snap])
        
        self.assertEqual(len(intents), 0)


if __name__ == "__main__":
    unittest.main()

