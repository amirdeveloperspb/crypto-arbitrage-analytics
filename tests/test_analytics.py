import unittest

from app.analytics.ml import OpportunityQualityModel
from app.analytics.opportunities import OpportunityAnalyzer
from app.core.market_data import MarketSnapshot


class OpportunityAnalyzerTest(unittest.TestCase):
    def test_uses_lowest_ask_and_highest_bid(self):
        snapshots = {
            "BINANCE": MarketSnapshot("BINANCE", "SOLUSDT", bid_price=99.8, ask_price=100.0, ask_size=8),
            "BYBIT": MarketSnapshot("BYBIT", "SOLUSDT", bid_price=101.0, ask_price=101.2, bid_size=7),
            "OKX": MarketSnapshot("OKX", "SOLUSDT", bid_price=100.4, ask_price=100.7, bid_size=3),
        }
        analyzer = OpportunityAnalyzer(
            budget_usd=1000.0,
            taker_fee_rate=0.001,
            max_age_seconds=2.0,
        )

        opportunity = analyzer.find_best("SOLUSDT", snapshots)

        self.assertIsNotNone(opportunity)
        self.assertEqual(opportunity["buy_on"], "BINANCE")
        self.assertEqual(opportunity["sell_on"], "BYBIT")
        self.assertAlmostEqual(opportunity["spread"], 1.0)
        self.assertGreater(opportunity["score"], 0)

    def test_quality_model_marks_positive_high_score_as_strong(self):
        quality = OpportunityQualityModel().predict_quality({
            "score": 75,
            "estimated_net_profit_usd": 4.2,
            "spread_pct": 0.4,
            "buy_size": 10,
            "sell_size": 9,
        })

        self.assertEqual(quality["quality"], "strong")
        self.assertEqual(quality["model"], "fast_explainable_quality_v2")
        self.assertGreater(quality["probability"], 0.65)
        self.assertGreater(quality["confidence"], 0.5)
        self.assertIn("recommendation", quality)

    def test_quality_model_exposes_risk_factors_for_weak_signal(self):
        quality = OpportunityQualityModel().predict_quality({
            "score": 20,
            "estimated_net_profit_usd": -1.0,
            "gross_profit_usd": 0.3,
            "estimated_fees_usd": 1.3,
            "spread_pct": 0.01,
            "buy_size": 0.5,
            "sell_size": 0.4,
        })

        self.assertEqual(quality["quality"], "weak")
        self.assertLess(quality["probability"], 0.5)
        self.assertTrue(quality["risk_factors"])


if __name__ == "__main__":
    unittest.main()
