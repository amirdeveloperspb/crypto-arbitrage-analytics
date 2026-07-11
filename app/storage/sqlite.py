import asyncio
import sqlite3
import time
from pathlib import Path
from typing import Iterable

from app.core.market_data import MarketSnapshot


class SQLiteHistory:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS market_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL NOT NULL,
                    exchange TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    bid_price REAL NOT NULL,
                    ask_price REAL NOT NULL,
                    bid_size REAL NOT NULL,
                    ask_size REAL NOT NULL,
                    last_price REAL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS opportunities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL NOT NULL,
                    symbol TEXT NOT NULL,
                    buy_on TEXT NOT NULL,
                    sell_on TEXT NOT NULL,
                    buy_price REAL NOT NULL,
                    sell_price REAL NOT NULL,
                    spread REAL NOT NULL,
                    spread_pct REAL NOT NULL,
                    gross_profit_usd REAL NOT NULL,
                    estimated_fees_usd REAL NOT NULL,
                    estimated_net_profit_usd REAL NOT NULL,
                    score REAL NOT NULL,
                    quality TEXT
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_snapshots_symbol_ts ON market_snapshots(symbol, ts)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_opportunities_symbol_ts ON opportunities(symbol, ts)"
            )

    def save_snapshots(self, snapshots: Iterable[MarketSnapshot]) -> None:
        rows = [
            (
                snapshot.timestamp,
                snapshot.exchange,
                snapshot.symbol,
                snapshot.bid_price,
                snapshot.ask_price,
                snapshot.bid_size,
                snapshot.ask_size,
                snapshot.last_price,
            )
            for snapshot in snapshots
        ]
        if not rows:
            return

        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO market_snapshots (
                    ts, exchange, symbol, bid_price, ask_price, bid_size, ask_size, last_price
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )

    def save_opportunity(self, opportunity: dict, quality: dict | None = None) -> None:
        if not opportunity:
            return

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO opportunities (
                    ts, symbol, buy_on, sell_on, buy_price, sell_price, spread,
                    spread_pct, gross_profit_usd, estimated_fees_usd,
                    estimated_net_profit_usd, score, quality
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    time.time(),
                    opportunity["symbol"],
                    opportunity["buy_on"],
                    opportunity["sell_on"],
                    opportunity["buy_price"],
                    opportunity["sell_price"],
                    opportunity["spread"],
                    opportunity["spread_pct"],
                    opportunity["gross_profit_usd"],
                    opportunity["estimated_fees_usd"],
                    opportunity["estimated_net_profit_usd"],
                    opportunity["score"],
                    quality.get("quality") if quality else None,
                ),
            )

    def get_summary(self, symbol: str, lookback_seconds: int = 3600) -> dict:
        since = time.time() - lookback_seconds
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*),
                    MAX(spread_pct),
                    AVG(spread_pct),
                    MAX(estimated_net_profit_usd),
                    AVG(score)
                FROM opportunities
                WHERE symbol = ? AND ts >= ?
                """,
                (symbol, since),
            ).fetchone()

        return {
            "symbol": symbol,
            "lookback_seconds": lookback_seconds,
            "opportunity_count": row[0] or 0,
            "max_spread_pct": row[1],
            "avg_spread_pct": row[2],
            "max_net_profit_usd": row[3],
            "avg_score": row[4],
        }

    def get_recent_opportunities(self, symbol: str, limit: int = 20) -> list[dict]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT
                    ts, symbol, buy_on, sell_on, buy_price, sell_price, spread,
                    spread_pct, gross_profit_usd, estimated_fees_usd,
                    estimated_net_profit_usd, score, quality
                FROM opportunities
                WHERE symbol = ?
                ORDER BY ts DESC
                LIMIT ?
                """,
                (symbol, limit),
            ).fetchall()

        return [dict(row) for row in rows]


async def history_loop(
    state,
    symbols: tuple[str, ...],
    history: SQLiteHistory,
    analyzer,
    quality_model,
    interval_seconds: float,
) -> None:
    while True:
        await asyncio.sleep(interval_seconds)
        for symbol in symbols:
            snapshots = state.get_all_for_symbol(symbol)
            history.save_snapshots(snapshots.values())
            opportunity = analyzer.find_best(symbol, snapshots)
            quality = quality_model.predict_quality(opportunity)
            if opportunity:
                history.save_opportunity(opportunity, quality)
