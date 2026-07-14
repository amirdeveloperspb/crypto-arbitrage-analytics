import csv
import tempfile
import unittest
from pathlib import Path

from app.storage.sqlite import SQLiteHistory
from scripts.export_dataset import export_dataset


class DatasetExportTest(unittest.TestCase):
    def test_exports_opportunities_to_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "history.sqlite3")
            out_path = str(Path(tmp) / "dataset.csv")
            history = SQLiteHistory(db_path)
            history.save_opportunity(
                {
                    "symbol": "SOLUSDT",
                    "buy_on": "BINANCE",
                    "sell_on": "OKX",
                    "buy_price": 100.0,
                    "sell_price": 101.0,
                    "spread": 1.0,
                    "spread_pct": 1.0,
                    "gross_profit_usd": 5.0,
                    "estimated_fees_usd": 1.0,
                    "estimated_net_profit_usd": 4.0,
                    "score": 88.0,
                },
                quality={"quality": "strong"},
            )

            count = export_dataset(db_path=db_path, output_path=out_path)

            self.assertEqual(count, 1)
            with open(out_path, newline="", encoding="utf-8") as file:
                rows = list(csv.DictReader(file))
            self.assertEqual(rows[0]["symbol"], "SOLUSDT")
            self.assertEqual(rows[0]["positive_after_fees"], "1")
            self.assertIn("fee_drag", rows[0])


if __name__ == "__main__":
    unittest.main()
