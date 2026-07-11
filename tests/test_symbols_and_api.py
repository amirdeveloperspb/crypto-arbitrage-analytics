import unittest

from app.api.fastapi_app import demo_execution, demo_opportunity, status
from app.core.market_data import MarketDataState, MarketSnapshot
from app.core.symbols import normalize_symbol, to_gate_symbol, to_okx_spot_symbol


class SymbolsAndApiTest(unittest.TestCase):
    def test_symbol_normalization(self):
        self.assertEqual(normalize_symbol("BTC-USDT"), "BTCUSDT")
        self.assertEqual(normalize_symbol("BTC_USDT"), "BTCUSDT")
        self.assertEqual(to_okx_spot_symbol("ETHUSDT"), "ETH-USDT")
        self.assertEqual(to_gate_symbol("SOLUSDT"), "SOL_USDT")

    def test_invalid_snapshot_is_rejected(self):
        state = MarketDataState(throttle_ms=0)
        accepted = state.update(
            MarketSnapshot(
                exchange="TEST",
                symbol="SOLUSDT",
                bid_price=101.0,
                ask_price=100.0,
            )
        )

        self.assertFalse(accepted)
        self.assertEqual(state.get_all_for_symbol("SOLUSDT"), {})

    def test_fastapi_status_and_demo_opportunity(self):
        status_payload = status()
        demo_payload = demo_opportunity("SOLUSDT")
        execution_payload = demo_execution("SOLUSDT", size=10)

        self.assertEqual(status_payload["status"], "ok")
        self.assertEqual(demo_payload["mode"], "demo")
        self.assertIn("opportunity", demo_payload)
        self.assertEqual(execution_payload["mode"], "demo")
        self.assertIn("execution", execution_payload)
        self.assertGreater(execution_payload["execution"]["estimated_net_profit_usd"], 0)


if __name__ == "__main__":
    unittest.main()
