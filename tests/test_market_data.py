import time
import unittest

from app.core.market_data import MarketDataState, PriceTick


class MarketDataStateTest(unittest.TestCase):
    def test_best_spread_uses_fresh_prices_only(self):
        state = MarketDataState(throttle_ms=0)
        state.update(PriceTick("BINANCE", "SOLUSDT", 100.0))
        state.update(PriceTick("BYBIT", "SOLUSDT", 101.0))
        old_tick = PriceTick("OKX", "SOLUSDT", 200.0)
        old_tick.timestamp = time.time() - 10
        state.update(old_tick)

        best = state.get_best_spread("SOLUSDT", max_age_seconds=2.0)

        self.assertIsNotNone(best)
        self.assertEqual(best["buy_on"], "BINANCE")
        self.assertEqual(best["sell_on"], "BYBIT")
        self.assertEqual(best["spread"], 1.0)

    def test_estimated_opportunity_subtracts_taker_fees(self):
        state = MarketDataState(throttle_ms=0)
        state.update(PriceTick("BINANCE", "SOLUSDT", 100.0))
        state.update(PriceTick("BYBIT", "SOLUSDT", 101.0))

        opportunity = state.get_estimated_opportunity(
            symbol="SOLUSDT",
            budget_usd=1000.0,
            taker_fee_rate=0.001,
            max_age_seconds=2.0,
        )

        self.assertIsNotNone(opportunity)
        self.assertEqual(opportunity["buy_on"], "BINANCE")
        self.assertEqual(opportunity["sell_on"], "BYBIT")
        self.assertAlmostEqual(opportunity["gross_profit_usd"], 10.0)
        self.assertAlmostEqual(opportunity["estimated_fees_usd"], 2.01)
        self.assertAlmostEqual(opportunity["estimated_net_profit_usd"], 7.99)
        self.assertTrue(opportunity["is_positive_after_fees"])


if __name__ == "__main__":
    unittest.main()
