import asyncio
import json
import unittest

from app.core.market_data import MarketDataState, PriceTick
from app.analytics.ml import OpportunityQualityModel
from app.web.server import WebDashboard


class WebApiTest(unittest.TestCase):
    def test_api_opportunity_returns_json_estimate(self):
        state = MarketDataState(throttle_ms=0)
        state.update(PriceTick("BINANCE", "SOLUSDT", 100.0))
        state.update(PriceTick("BYBIT", "SOLUSDT", 102.0))

        dashboard = WebDashboard(
            state,
            symbol="SOLUSDT",
            budget_usd=500.0,
            taker_fee_rate=0.001,
            max_price_age_seconds=2.0,
            quality_model=OpportunityQualityModel(),
        )

        response = asyncio.run(dashboard.api_opportunity(None))
        payload = json.loads(response.text)

        self.assertEqual(payload["symbol"], "SOLUSDT")
        self.assertEqual(payload["opportunity"]["buy_on"], "BINANCE")
        self.assertEqual(payload["opportunity"]["sell_on"], "BYBIT")
        self.assertIn("probability", payload["quality"])
        self.assertIn("risk_factors", payload["quality"])
        self.assertIn("not an executable trading signal", payload["note"])


if __name__ == "__main__":
    unittest.main()
