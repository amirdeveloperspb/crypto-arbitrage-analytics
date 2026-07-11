from fastapi import FastAPI, Query

from app.analytics.execution import ExecutionQualityAnalyzer
from app.analytics.ml import OpportunityQualityModel
from app.analytics.opportunities import OpportunityAnalyzer
from app.config import (
    HISTORY_DB_PATH,
    MAX_PRICE_AGE_SECONDS,
    TAKER_FEE_RATE,
    TRADING_BUDGET,
    TRADING_SYMBOL,
    TRADING_SYMBOLS,
)
from app.core.market_data import MarketSnapshot, OrderBookLevel, OrderBookSnapshot
from app.demo import BASE_PRICES, EXCHANGE_OFFSETS
from app.storage.sqlite import SQLiteHistory


app = FastAPI(
    title="Crypto Arbitrage Analytics API",
    version="0.2.0",
    description="OpenAPI backend for inspecting symbols, demo opportunities, and SQLite history.",
)

history = SQLiteHistory(HISTORY_DB_PATH)
analyzer = OpportunityAnalyzer(
    budget_usd=TRADING_BUDGET,
    taker_fee_rate=TAKER_FEE_RATE,
    max_age_seconds=MAX_PRICE_AGE_SECONDS,
)
quality_model = OpportunityQualityModel()
execution_analyzer = ExecutionQualityAnalyzer(
    taker_fee_rate=TAKER_FEE_RATE,
    max_age_seconds=MAX_PRICE_AGE_SECONDS,
)


def _valid_symbol(symbol: str) -> str:
    normalized = symbol.upper()
    return normalized if normalized in TRADING_SYMBOLS else TRADING_SYMBOL


def _demo_snapshots(symbol: str) -> dict[str, MarketSnapshot]:
    base = BASE_PRICES.get(symbol, 100.0)
    snapshots = {}
    for exchange, offset in EXCHANGE_OFFSETS.items():
        mid = base * (1 + offset)
        spread = max(base * 0.00012, 0.01)
        snapshots[exchange] = MarketSnapshot(
            exchange=exchange,
            symbol=symbol,
            bid_price=mid - spread / 2,
            ask_price=mid + spread / 2,
            bid_size=15,
            ask_size=14,
            last_price=mid,
        )
    return snapshots


def _demo_order_books(symbol: str) -> dict[str, OrderBookSnapshot]:
    base = BASE_PRICES.get(symbol, 100.0)
    books = {}
    for exchange, offset in EXCHANGE_OFFSETS.items():
        mid = base * (1 + offset)
        spread = max(base * 0.00012, 0.01)
        gap = max(base * 0.00008, 0.01)
        books[exchange] = OrderBookSnapshot(
            exchange=exchange,
            symbol=symbol,
            bids=[OrderBookLevel(mid - spread / 2 - i * gap, 8 + i * 3) for i in range(6)],
            asks=[OrderBookLevel(mid + spread / 2 + i * gap, 8 + i * 2) for i in range(6)],
        )
    return books


@app.get("/api/status")
def status():
    return {
        "status": "ok",
        "default_symbol": TRADING_SYMBOL,
        "symbols": TRADING_SYMBOLS,
        "history_db_path": HISTORY_DB_PATH,
    }


@app.get("/api/symbols")
def symbols():
    return {
        "default_symbol": TRADING_SYMBOL,
        "symbols": TRADING_SYMBOLS,
    }


@app.get("/api/demo/opportunity")
def demo_opportunity(symbol: str = Query(default=TRADING_SYMBOL)):
    symbol = _valid_symbol(symbol)
    opportunity = analyzer.find_best(symbol, _demo_snapshots(symbol))
    return {
        "symbol": symbol,
        "opportunity": opportunity,
        "quality": quality_model.predict_quality(opportunity),
        "mode": "demo",
    }


@app.get("/api/demo/execution")
def demo_execution(symbol: str = Query(default=TRADING_SYMBOL), size: float = 10.0):
    symbol = _valid_symbol(symbol)
    result = execution_analyzer.find_best_executable(symbol, _demo_order_books(symbol), target_size=size)
    return {
        "symbol": symbol,
        "target_size": size,
        "execution": result,
        "mode": "demo",
    }


@app.get("/api/history")
def history_summary(symbol: str = Query(default=TRADING_SYMBOL), lookback_seconds: int = 3600):
    symbol = _valid_symbol(symbol)
    return history.get_summary(symbol, lookback_seconds=lookback_seconds)


@app.get("/api/opportunities")
def recent_opportunities(symbol: str = Query(default=TRADING_SYMBOL), limit: int = 20):
    symbol = _valid_symbol(symbol)
    return {
        "symbol": symbol,
        "opportunities": history.get_recent_opportunities(symbol, limit=limit),
    }
