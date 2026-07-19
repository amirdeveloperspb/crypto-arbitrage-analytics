# app/web/server.py
import asyncio
import json
import os
from datetime import datetime

import aiohttp
from aiohttp import web

from app.analytics.execution import ExecutionQualityAnalyzer
from app.analytics.opportunities import summarize_prices
from app.core.market_data import OrderBookLevel, OrderBookSnapshot


class WebDashboard:

    def __init__(
        self,
        state,
        symbol: str,
        budget_usd: float,
        taker_fee_rate: float,
        max_price_age_seconds: float,
        symbols: tuple[str, ...] = ("SOLUSDT",),
        history=None,
        analyzer=None,
        quality_model=None,
        min_spread_pct: float = 0.0,
        host='localhost',
        port=8080,
    ):
        self.state = state
        self.symbol = symbol
        self.budget_usd = budget_usd
        self.taker_fee_rate = taker_fee_rate
        self.max_price_age_seconds = max_price_age_seconds
        self.symbols = symbols
        self.history = history
        self.analyzer = analyzer
        self.quality_model = quality_model
        self.min_spread_pct = min_spread_pct
        self.host = host
        self.port = port
        self.app = web.Application()
        self._runner = None
        self._setup_routes()
        self._clients = []

    def _setup_routes(self):
        self.app.router.add_get('/', self.index)
        self.app.router.add_get('/docs/ru', self.docs_ru)
        self.app.router.add_get('/docs/en', self.docs_en)
        self.app.router.add_get('/ws', self.websocket_handler)
        self.app.router.add_get('/api/health', self.api_health)
        self.app.router.add_get('/api/symbols', self.api_symbols)
        self.app.router.add_get('/api/prices', self.api_prices)
        self.app.router.add_get('/api/opportunity', self.api_opportunity)
        self.app.router.add_get('/api/execution', self.api_execution)
        self.app.router.add_get('/api/opportunities', self.api_opportunities)
        self.app.router.add_get('/api/history', self.api_history)

        static_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
        os.makedirs(static_path, exist_ok=True)
        self.app.router.add_static('/static/', path=static_path, name='static')

    async def docs_ru(self, request):
        html = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Документация проекта</title>
    <style>
        body { margin: 0; background: #eef2f5; color: #18212f; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif; padding: 32px; line-height: 1.55; }
        main { max-width: 880px; margin: 0 auto; background: white; border: 1px solid #d7dee6; border-radius: 8px; padding: 28px; }
        code { background: #eef2f5; padding: 2px 5px; border-radius: 4px; }
        pre { background: #eef2f5; padding: 14px; border-radius: 8px; overflow: auto; }
        a { color: #2f6f9f; }
    </style>
</head>
<body>
<main>
    <h1>Crypto Arbitrage Analytics</h1>
    <p>Проект анализирует потенциальные арбитражные возможности между биржами. Главная техническая особенность — оценка исполнимости по стаканам заявок.</p>
    <h2>Что делает алгоритм</h2>
    <ol>
        <li>Берет стаканы заявок с бирж.</li>
        <li>Моделирует покупку объема по уровням <code>ask</code>.</li>
        <li>Моделирует продажу такого же объема по уровням <code>bid</code>.</li>
        <li>Считает средневзвешенные цены VWAP.</li>
        <li>Вычитает торговые комиссии.</li>
        <li>Показывает проскальзывание, чистую прибыль и score.</li>
    </ol>
    <h2>Запуск для защиты</h2>
    <pre>HOME_SERVER_MODE=true DEMO_MODE=true .venv/bin/python -m app.main</pre>
    <h2>API</h2>
    <pre>GET /api/execution?symbol=SOLUSDT&amp;size=10</pre>
    <p><a href="/">Вернуться к dashboard</a></p>
</main>
</body>
</html>
        """
        return web.Response(text=html, content_type="text/html")

    async def docs_en(self, request):
        html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Project Documentation</title>
    <style>
        body { margin: 0; background: #eef2f5; color: #18212f; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif; padding: 32px; line-height: 1.55; }
        main { max-width: 880px; margin: 0 auto; background: white; border: 1px solid #d7dee6; border-radius: 8px; padding: 28px; }
        code { background: #eef2f5; padding: 2px 5px; border-radius: 4px; }
        pre { background: #eef2f5; padding: 14px; border-radius: 8px; overflow: auto; }
        a { color: #2f6f9f; }
    </style>
</head>
<body>
<main>
    <h1>Crypto Arbitrage Analytics</h1>
    <p>The project analyzes potential arbitrage opportunities across exchanges. The main technical feature is order-book execution estimation.</p>
    <h2>What the algorithm does</h2>
    <ol>
        <li>Fetches order-book snapshots from exchanges.</li>
        <li>Simulates buying target size through <code>ask</code> levels.</li>
        <li>Simulates selling the same size through <code>bid</code> levels.</li>
        <li>Calculates VWAP buy and sell prices.</li>
        <li>Subtracts trading fees.</li>
        <li>Reports slippage, net result, and signal score.</li>
    </ol>
    <h2>Defense demo command</h2>
    <pre>HOME_SERVER_MODE=true DEMO_MODE=true .venv/bin/python -m app.main</pre>
    <h2>API</h2>
    <pre>GET /api/execution?symbol=SOLUSDT&amp;size=10</pre>
    <p><a href="/">Back to dashboard</a></p>
</main>
</body>
</html>
        """
        return web.Response(text=html, content_type="text/html")

    async def index(self, request):
        dashboard_config = {
            "symbols": list(self.symbols),
            "defaultSymbol": self.symbol,
            "minSpreadPct": self.min_spread_pct,
        }
        html = self._render_template(
            "dashboard.html",
            {"__DASHBOARD_CONFIG__": json.dumps(dashboard_config)},
        )
        return web.Response(text=html, content_type='text/html')

    def _render_template(self, template_name: str, replacements: dict[str, str] | None = None) -> str:
        template_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'templates',
            template_name,
        )
        with open(template_path, encoding='utf-8') as template_file:
            html = template_file.read()
        for key, value in (replacements or {}).items():
            html = html.replace(key, value)
        return html

    def _request_symbol(self, request) -> str:
        if request is None:
            return self.symbol
        symbol = request.query.get("symbol", self.symbol).upper()
        if symbol not in self.symbols:
            return self.symbol
        return symbol

    async def api_health(self, request):
        symbol = self._request_symbol(request)
        prices = self.state.get_all_for_symbol(
            symbol,
            max_age_seconds=self.max_price_age_seconds,
        )
        return web.json_response({
            "status": "ok" if len(prices) >= 2 else "waiting_for_market_data",
            "symbol": symbol,
            "fresh_exchanges": sorted(prices.keys()),
            "required_fresh_exchanges": 2,
            "max_price_age_seconds": self.max_price_age_seconds,
        })

    async def api_symbols(self, request):
        return web.json_response({
            "default_symbol": self.symbol,
            "symbols": list(self.symbols),
        })

    async def api_prices(self, request):
        symbol = self._request_symbol(request)
        prices = self.state.get_all_for_symbol(symbol)
        return web.json_response(summarize_prices(symbol, prices, self.max_price_age_seconds))

    async def api_opportunity(self, request):
        symbol = self._request_symbol(request)
        snapshots = self.state.get_all_for_symbol(symbol)
        opportunity = (
            self.analyzer.find_best(symbol, snapshots)
            if self.analyzer
            else self.state.get_estimated_opportunity(
                symbol=symbol,
                budget_usd=self.budget_usd,
                taker_fee_rate=self.taker_fee_rate,
                max_age_seconds=self.max_price_age_seconds,
            )
        )
        quality = self.quality_model.predict_quality(opportunity) if self.quality_model else None
        return web.json_response({
            "symbol": symbol,
            "opportunity": opportunity,
            "quality": quality,
            "note": "This is an estimate based on top-of-book bid/ask, not an executable trading signal.",
        })

    async def api_execution(self, request):
        symbol = self._request_symbol(request)
        size = float(request.query.get("size", "10")) if request else 10.0
        scenario = request.query.get("scenario", "live") if request else "live"
        analyzer = ExecutionQualityAnalyzer(
            taker_fee_rate=self.taker_fee_rate,
            max_age_seconds=self.max_price_age_seconds,
        )
        order_books = (
            self._demo_execution_books(symbol, scenario)
            if scenario != "live"
            else self.state.get_order_books_for_symbol(symbol)
        )
        result = analyzer.find_best_executable(
            symbol=symbol,
            order_books=order_books,
            target_size=size,
        )
        note = "Execution estimate walks visible order-book levels and compares raw spread with VWAP net result."
        if scenario == "liquidity" and result is None:
            note = "Rejected: visible order-book depth cannot fill the selected size on both sides."
        elif scenario == "stale" and result is None:
            note = "Rejected: order-book snapshots are older than the allowed freshness window."
        return web.json_response({
            "symbol": symbol,
            "target_size": size,
            "scenario": scenario,
            "execution": result,
            "note": note,
        })

    def _demo_execution_books(self, symbol: str, scenario: str) -> dict[str, OrderBookSnapshot]:
        now = datetime.now().timestamp()
        if scenario == "profitable":
            return {
                "DEMO_BUY": self._book(
                    "DEMO_BUY",
                    symbol,
                    bids=[(99.90, 25), (99.80, 25)],
                    asks=[(100.00, 25), (100.05, 25)],
                    timestamp=now,
                ),
                "DEMO_SELL": self._book(
                    "DEMO_SELL",
                    symbol,
                    bids=[(100.55, 25), (100.50, 25)],
                    asks=[(100.65, 25), (100.70, 25)],
                    timestamp=now,
                ),
            }
        if scenario == "slippage":
            return {
                "DEMO_BUY": self._book(
                    "DEMO_BUY",
                    symbol,
                    bids=[(98.00, 25), (97.80, 25)],
                    asks=[(100.00, 1), (101.00, 40), (101.25, 40)],
                    timestamp=now,
                ),
                "DEMO_SELL": self._book(
                    "DEMO_SELL",
                    symbol,
                    bids=[(100.70, 1), (99.80, 40), (99.60, 40)],
                    asks=[(103.00, 25), (103.20, 25)],
                    timestamp=now,
                ),
            }
        if scenario == "liquidity":
            return {
                "DEMO_BUY": self._book(
                    "DEMO_BUY",
                    symbol,
                    bids=[(99.90, 3)],
                    asks=[(100.00, 3)],
                    timestamp=now,
                ),
                "DEMO_SELL": self._book(
                    "DEMO_SELL",
                    symbol,
                    bids=[(101.00, 2)],
                    asks=[(101.20, 2)],
                    timestamp=now,
                ),
            }
        if scenario == "stale":
            stale_time = now - self.max_price_age_seconds - 5
            return {
                "DEMO_BUY": self._book(
                    "DEMO_BUY",
                    symbol,
                    bids=[(99.90, 25)],
                    asks=[(100.00, 25)],
                    timestamp=stale_time,
                ),
                "DEMO_SELL": self._book(
                    "DEMO_SELL",
                    symbol,
                    bids=[(101.00, 25)],
                    asks=[(101.20, 25)],
                    timestamp=stale_time,
                ),
            }
        return self.state.get_order_books_for_symbol(symbol)

    def _book(
        self,
        exchange: str,
        symbol: str,
        bids: list[tuple[float, float]],
        asks: list[tuple[float, float]],
        timestamp: float,
    ) -> OrderBookSnapshot:
        return OrderBookSnapshot(
            exchange=exchange,
            symbol=symbol,
            bids=[OrderBookLevel(price=price, size=size) for price, size in bids],
            asks=[OrderBookLevel(price=price, size=size) for price, size in asks],
            timestamp=timestamp,
        )

    async def api_history(self, request):
        symbol = self._request_symbol(request)
        if not self.history:
            return web.json_response({"symbol": symbol, "history": None})
        return web.json_response(self.history.get_summary(symbol))

    async def api_opportunities(self, request):
        symbol = self._request_symbol(request)
        limit = int(request.query.get("limit", "20")) if request else 20
        if not self.history:
            return web.json_response({"symbol": symbol, "opportunities": []})
        return web.json_response({
            "symbol": symbol,
            "opportunities": self.history.get_recent_opportunities(symbol, limit=limit),
        })

    async def websocket_handler(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        self._clients.append(ws)
        print(f"[WEB] Client connected. Total: {len(self._clients)}")

        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    if msg.data == 'close':
                        await ws.close()
        finally:
            self._clients.remove(ws)
            print(f"[WEB] Client disconnected. Total: {len(self._clients)}")

        return ws

    async def broadcast(self):
        while True:
            await asyncio.sleep(0.5)

            now = datetime.now().timestamp()
            symbols_data = {}
            for symbol in self.symbols:
                snapshots = self.state.get_all_for_symbol(symbol)
                best = self.state.get_best_spread(
                    symbol,
                    max_age_seconds=self.max_price_age_seconds,
                )
                exchanges = {}
                for exchange in ("BINANCE", "BYBIT", "OKX", "GATEIO"):
                    snapshot = snapshots.get(exchange)
                    exchanges[exchange] = {
                        "bid_price": snapshot.bid_price,
                        "ask_price": snapshot.ask_price,
                        "last_price": snapshot.last_price,
                        "price": snapshot.price,
                        "age": f"{now - snapshot.timestamp:.1f}s",
                        "live": now - snapshot.timestamp < self.max_price_age_seconds,
                    } if snapshot else None

                symbols_data[symbol] = {
                    "exchanges": exchanges,
                    "fresh_count": sum(1 for item in exchanges.values() if item and item["live"]),
                    "exchange_count": len(exchanges),
                    "spread": best["spread"] if best else None,
                    "route": f"{best['buy_on']} → {best['sell_on']}" if best else None,
                }

            data = {
                "symbols": symbols_data,
                "time": datetime.now().strftime("%H:%M:%S.%f")[:-3]
            }

            message = json.dumps(data)

            disconnected = []
            for client in self._clients:
                if not client.closed:
                    await client.send_str(message)
                else:
                    disconnected.append(client)

            for client in disconnected:
                self._clients.remove(client)

    async def start(self):
        self._runner = web.AppRunner(self.app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self.host, self.port)
        await site.start()
        print(f"[WEB] Dashboard running at http://{self.host}:{self.port}")

        await self.broadcast()

    async def stop(self):
        if self._runner:
            await self._runner.cleanup()
