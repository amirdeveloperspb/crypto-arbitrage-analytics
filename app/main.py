# app/main.py
import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.market_data import MarketDataState
from app.analytics.execution import ExecutionQualityAnalyzer
from app.analytics.ml import OpportunityQualityModel
from app.analytics.opportunities import OpportunityAnalyzer
from app.demo import demo_market_loop
from app.exchanges.binance import BinanceWebSocket
from app.exchanges.bybit import BybitWebSocket
from app.exchanges.gateio import GateIOWebSocket
from app.exchanges.okx import OKXWebSocket
from app.exchanges.funding import FundingRateFetcher
from app.exchanges.order_books import OrderBookRestFetcher
from app.display.terminal import DisplayEngine
from app.storage.sqlite import SQLiteHistory, history_loop
from app.web.server import WebDashboard
from app.logging_config import configure_logging
from app.network import dashboard_urls

try:
    from app.config import (
        MAX_PRICE_AGE_SECONDS,
        DEMO_MODE,
        HOME_SERVER_MODE,
        HISTORY_DB_PATH,
        HISTORY_FLUSH_INTERVAL_SECONDS,
        MIN_SPREAD_PCT,
        TAKER_FEE_RATE,
        TELEGRAM_ALERT_COOLDOWN_SECONDS,
        TELEGRAM_ALERT_MIN_SCORE,
        TELEGRAM_BOT_TOKEN,
        TELEGRAM_CHAT_ID,
        TELEGRAM_COMMANDS_ENABLED,
        TRADING_BUDGET,
        TRADING_SYMBOL,
        TRADING_SYMBOLS,
        WEB_HOST,
        WEB_PORT,
    )
    from app.notifiers.telegram import TelegramNotifier

    TELEGRAM_ENABLED = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
except ImportError:
    TELEGRAM_ENABLED = False
    TelegramNotifier = None
    TRADING_SYMBOL = "SOLUSDT"
    TRADING_BUDGET = 500.0
    TAKER_FEE_RATE = 0.001
    MAX_PRICE_AGE_SECONDS = 2.0
    DEMO_MODE = False
    HOME_SERVER_MODE = False
    HISTORY_DB_PATH = "data/market_history.sqlite3"
    HISTORY_FLUSH_INTERVAL_SECONDS = 5.0
    MIN_SPREAD_PCT = 0.0
    TELEGRAM_COMMANDS_ENABLED = False
    TELEGRAM_ALERT_MIN_SCORE = 70.0
    TELEGRAM_ALERT_COOLDOWN_SECONDS = 180
    WEB_HOST = "localhost"
    WEB_PORT = 8080
    TRADING_SYMBOLS = ("SOLUSDT",)

SYMBOL = TRADING_SYMBOL
SYMBOLS = TRADING_SYMBOLS
logger = logging.getLogger(__name__)


async def funding_loop(funding: FundingRateFetcher, notifier):
    """Каждые 5 минут проверяем funding rates."""
    while True:
        await funding.update_all()
        print(f"\n[FUNDING]\n{funding}")

        opp = funding.get_best_opportunity()
        if opp and opp["profit_rate"] > 0.0001:  # > 0.01%
            msg = (
                f"💰 <b>FUNDING ARBITRAGE</b>\n\n"
                f"Short: {opp['short_on']} ({opp['rates'][opp['short_on']] * 100:+.4f}%)\n"
                f"Long:  {opp['long_on']} ({opp['rates'][opp['long_on']] * 100:+.4f}%)\n"
                f"Profit: {opp['profit_rate'] * 100:.4f}% per 8h\n\n"
                f"With $500: ${500 * opp['profit_rate']:.2f} per 8h"
            )
            print(f"[FUNDING ALERT] {msg}")
            if notifier:
                await notifier.send_message(msg)

        await asyncio.sleep(300)  # 5 минут


async def opportunity_alert_loop(state, symbols, analyzer, quality_model, notifier):
    while True:
        await asyncio.sleep(2)
        if not notifier:
            continue
        for symbol in symbols:
            opportunity = analyzer.find_best(symbol, state.get_all_for_symbol(symbol))
            quality = quality_model.predict_quality(opportunity)
            await notifier.alert_opportunity(
                opportunity=opportunity,
                quality=quality,
                min_score=TELEGRAM_ALERT_MIN_SCORE,
                cooldown_seconds=TELEGRAM_ALERT_COOLDOWN_SECONDS,
            )


async def main():
    configure_logging()
    state = MarketDataState(throttle_ms=100)
    funding = FundingRateFetcher()
    analyzer = OpportunityAnalyzer(
        budget_usd=TRADING_BUDGET,
        taker_fee_rate=TAKER_FEE_RATE,
        max_age_seconds=MAX_PRICE_AGE_SECONDS,
    )
    execution_analyzer = ExecutionQualityAnalyzer(
        taker_fee_rate=TAKER_FEE_RATE,
        max_age_seconds=MAX_PRICE_AGE_SECONDS,
    )
    quality_model = OpportunityQualityModel()
    history = SQLiteHistory(HISTORY_DB_PATH)

    # Telegram
    notifier = None
    if TELEGRAM_ENABLED:
        notifier = TelegramNotifier(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
        await notifier.send_startup(SYMBOLS, demo_mode=DEMO_MODE)

    # Web Dashboard
    dashboard = WebDashboard(
        state,
        symbol=SYMBOL,
        budget_usd=TRADING_BUDGET,
        taker_fee_rate=TAKER_FEE_RATE,
        max_price_age_seconds=MAX_PRICE_AGE_SECONDS,
        symbols=SYMBOLS,
        history=history,
        analyzer=analyzer,
        quality_model=quality_model,
        min_spread_pct=MIN_SPREAD_PCT,
        host=WEB_HOST,
        port=WEB_PORT,
    )

    # Terminal display
    display = DisplayEngine(
        state,
        symbol=SYMBOL,
        max_price_age_seconds=MAX_PRICE_AGE_SECONDS,
        throttle_ms=500,
    )

    binance = BinanceWebSocket(state, SYMBOLS)
    bybit = BybitWebSocket(state, SYMBOLS)
    okx = OKXWebSocket(state, SYMBOLS)
    gateio = GateIOWebSocket(state, SYMBOLS)
    order_books = OrderBookRestFetcher(state, SYMBOLS)

    tasks = []

    try:
        print("=" * 60)
        print("  CRYPTO ARBITRAGE ANALYTICS")
        print("=" * 60)
        print(f"  Monitoring: {', '.join(SYMBOLS)} market data and SOL funding rates")
        print(f"  Mode: {'DEMO' if DEMO_MODE else 'LIVE'}")
        print(f"  Exchanges: Binance, Bybit, OKX, Gate.io")
        print(f"  History DB: {HISTORY_DB_PATH}")
        print(f"  Check interval: 5 minutes")
        urls = dashboard_urls(WEB_HOST, WEB_PORT)
        print(f"  Web Dashboard local: {urls['local']}")
        if HOME_SERVER_MODE:
            print(f"  Web Dashboard phone: {urls['lan'] or 'LAN IP not detected'}")
        else:
            print("  Phone access: disabled (set HOME_SERVER_MODE=true)")
        print(f"  Telegram: {'enabled' if TELEGRAM_ENABLED else 'disabled'}")
        print("=" * 60)
        print("Press Ctrl+C to exit\n")

        await asyncio.sleep(1)

        tasks = []
        if DEMO_MODE:
            tasks.append(asyncio.create_task(demo_market_loop(state, SYMBOLS)))
        else:
            tasks.extend([
                asyncio.create_task(binance.start()),
                asyncio.create_task(bybit.start()),
                asyncio.create_task(okx.start()),
                asyncio.create_task(gateio.start()),
                asyncio.create_task(order_books.start()),
            ])

        tasks.extend([
            asyncio.create_task(display.start()),
            asyncio.create_task(dashboard.start()),
            asyncio.create_task(
                history_loop(
                    state=state,
                    symbols=SYMBOLS,
                    history=history,
                    analyzer=analyzer,
                    quality_model=quality_model,
                    interval_seconds=HISTORY_FLUSH_INTERVAL_SECONDS,
                )
            ),
            asyncio.create_task(opportunity_alert_loop(state, SYMBOLS, analyzer, quality_model, notifier)),
        ])
        if not DEMO_MODE:
            tasks.append(asyncio.create_task(funding_loop(funding, notifier)))
        if TELEGRAM_ENABLED and TELEGRAM_COMMANDS_ENABLED:
            from app.notifiers.telegram import telegram_command_loop

            tasks.append(asyncio.create_task(
                telegram_command_loop(
                    notifier=notifier,
                    state=state,
                    symbols=SYMBOLS,
                    analyzer=analyzer,
                    quality_model=quality_model,
                    demo_mode=DEMO_MODE,
                    execution_analyzer=execution_analyzer,
                )
            ))

        await asyncio.gather(*tasks)

    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    finally:
        print("\nShutting down...")
        if not DEMO_MODE:
            binance.stop()
            bybit.stop()
            okx.stop()
            gateio.stop()
            order_books.stop()
        display.stop()
        await dashboard.stop()

        for t in tasks:
            if not t.done():
                t.cancel()

        await asyncio.gather(*tasks, return_exceptions=True)

        if notifier:
            await notifier.send_message("⛔ <b>Bot Stopped</b>")

        print("Bye!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
