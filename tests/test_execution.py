import time
import unittest

from app.analytics.execution import ExecutionQualityAnalyzer
from app.core.market_data import OrderBookLevel, OrderBookSnapshot


class ExecutionQualityAnalyzerTest(unittest.TestCase):
    def _book(self, exchange, bids, asks, ts=None):
        return OrderBookSnapshot(
            exchange=exchange,
            symbol="SOLUSDT",
            bids=[OrderBookLevel(price, size) for price, size in bids],
            asks=[OrderBookLevel(price, size) for price, size in asks],
            timestamp=time.time() if ts is None else ts,
        )

    def test_vwap_fees_and_slippage_for_executable_route(self):
        buy_book = self._book(
            "BINANCE",
            bids=[(99.5, 10)],
            asks=[(100.0, 5), (101.0, 5)],
        )
        sell_book = self._book(
            "OKX",
            bids=[(103.0, 4), (102.0, 6)],
            asks=[(103.5, 10)],
        )
        analyzer = ExecutionQualityAnalyzer(taker_fee_rate=0.001, max_age_seconds=2.0)

        result = analyzer.evaluate_route("SOLUSDT", buy_book, sell_book, target_size=10)

        self.assertIsNotNone(result)
        self.assertAlmostEqual(result["average_buy_price"], 100.5)
        self.assertAlmostEqual(result["average_sell_price"], 102.4)
        self.assertAlmostEqual(result["gross_profit_usd"], 19.0)
        self.assertAlmostEqual(result["estimated_fees_usd"], 2.029)
        self.assertAlmostEqual(result["estimated_net_profit_usd"], 16.971)
        self.assertAlmostEqual(result["buy_slippage_pct"], 0.5)
        self.assertGreater(result["max_profitable_size"], 0)

    def test_rejects_stale_books(self):
        old = time.time() - 10
        books = {
            "BINANCE": self._book("BINANCE", bids=[(99, 10)], asks=[(100, 10)], ts=old),
            "OKX": self._book("OKX", bids=[(103, 10)], asks=[(104, 10)]),
        }
        analyzer = ExecutionQualityAnalyzer(taker_fee_rate=0.001, max_age_seconds=2.0)

        self.assertIsNone(analyzer.find_best_executable("SOLUSDT", books, target_size=1))

    def test_rejects_insufficient_liquidity_when_full_fill_required(self):
        buy_book = self._book("BINANCE", bids=[(99, 10)], asks=[(100, 1)])
        sell_book = self._book("OKX", bids=[(103, 1)], asks=[(104, 10)])
        analyzer = ExecutionQualityAnalyzer(taker_fee_rate=0.001, max_age_seconds=2.0)

        self.assertIsNone(analyzer.evaluate_route("SOLUSDT", buy_book, sell_book, target_size=3))


if __name__ == "__main__":
    unittest.main()
