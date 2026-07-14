import argparse
import csv
import sqlite3
from pathlib import Path


DEFAULT_DB_PATH = "data/market_history.sqlite3"
DEFAULT_OUTPUT_PATH = "data/opportunity_dataset.csv"


def export_dataset(db_path: str, output_path: str, symbol: str | None = None) -> int:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    query = """
        SELECT
            ts,
            symbol,
            buy_on,
            sell_on,
            buy_price,
            sell_price,
            spread,
            spread_pct,
            gross_profit_usd,
            estimated_fees_usd,
            estimated_net_profit_usd,
            score,
            quality,
            CASE
                WHEN estimated_net_profit_usd > 0 THEN 1
                ELSE 0
            END AS positive_after_fees,
            CASE
                WHEN ABS(gross_profit_usd) > 0
                THEN estimated_fees_usd / ABS(gross_profit_usd)
                ELSE 0
            END AS fee_drag
        FROM opportunities
    """
    params = []
    if symbol:
        query += " WHERE symbol = ?"
        params.append(symbol.upper())
    query += " ORDER BY ts ASC"

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, params).fetchall()

    fieldnames = [
        "ts",
        "symbol",
        "buy_on",
        "sell_on",
        "buy_price",
        "sell_price",
        "spread",
        "spread_pct",
        "gross_profit_usd",
        "estimated_fees_usd",
        "estimated_net_profit_usd",
        "score",
        "quality",
        "positive_after_fees",
        "fee_drag",
    ]
    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(dict(row) for row in rows)

    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export saved opportunity history to a CSV dataset.")
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help="SQLite database path.")
    parser.add_argument("--out", default=DEFAULT_OUTPUT_PATH, help="CSV output path.")
    parser.add_argument("--symbol", default=None, help="Optional symbol filter, for example SOLUSDT.")
    args = parser.parse_args()

    count = export_dataset(db_path=args.db, output_path=args.out, symbol=args.symbol)
    print(f"Exported {count} rows to {args.out}")


if __name__ == "__main__":
    main()
