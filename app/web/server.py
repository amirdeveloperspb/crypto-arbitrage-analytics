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
        html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Crypto Arbitrage Analytics</title>
    <style>
        :root {
            --bg: #eef2f5;
            --surface: #f8fafc;
            --surface-strong: #ffffff;
            --border: #d7dee6;
            --border-soft: #e6ebf0;
            --text: #18212f;
            --muted: #647386;
            --muted-soft: #8a97a8;
            --blue: #2f6f9f;
            --blue-soft: #d9eaf5;
            --green: #16784c;
            --green-soft: #dff2e9;
            --red: #b84a4a;
            --red-soft: #f6dfdf;
            --amber: #9b6a22;
            --shadow: 0 16px 42px rgba(38, 53, 71, 0.08);
            --shadow-soft: 0 6px 18px rgba(38, 53, 71, 0.06);
        }

        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            background:
                radial-gradient(circle at top left, rgba(217,234,245,0.48), transparent 32%),
                linear-gradient(180deg, rgba(255,255,255,0.82), rgba(238,242,245,0.96)),
                var(--bg);
            color: var(--text);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Arial, sans-serif;
            min-height: 100vh;
            padding: 28px;
        }

        .shell {
            max-width: 1180px;
            margin: 0 auto;
        }

        .topbar {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 18px;
            margin-bottom: 18px;
        }

        .eyebrow {
            color: var(--blue);
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0;
            text-transform: uppercase;
            margin-bottom: 7px;
        }

        h1 {
            margin: 0;
            font-size: 30px;
            line-height: 1.15;
            font-weight: 750;
        }

        .subtitle {
            margin-top: 8px;
            max-width: 720px;
            color: var(--muted);
            font-size: 14px;
            line-height: 1.5;
        }

        .connection {
            min-width: 220px;
            background: rgba(255,255,255,0.72);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 12px 14px;
            box-shadow: var(--shadow);
        }

        .top-actions {
            display: grid;
            gap: 10px;
        }

        .language-switch {
            display: flex;
            gap: 6px;
            justify-content: flex-end;
        }

        .language-switch button,
        .language-choice button {
            border: 1px solid var(--border);
            background: var(--surface-strong);
            color: var(--text);
            border-radius: 8px;
            padding: 8px 10px;
            font: inherit;
            font-weight: 700;
            cursor: pointer;
        }

        .language-switch button.active {
            color: var(--blue);
            background: var(--blue-soft);
            border-color: #afcbdc;
        }

        .language-modal {
            position: fixed;
            inset: 0;
            background: rgba(24, 33, 47, 0.28);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            padding: 20px;
        }

        .language-modal.open {
            display: flex;
        }

        .language-card {
            width: min(420px, 100%);
            background: white;
            border: 1px solid var(--border);
            border-radius: 10px;
            box-shadow: var(--shadow);
            padding: 24px;
        }

        .language-card h2 {
            margin: 0 0 8px;
            font-size: 22px;
        }

        .language-card p {
            margin: 0 0 18px;
            color: var(--muted);
        }

        .language-choice {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }

        .toolbar {
            display: flex;
            align-items: center;
            gap: 10px;
            margin: 16px 0;
            padding: 10px;
            background: rgba(255,255,255,0.64);
            border: 1px solid var(--border-soft);
            border-radius: 8px;
            box-shadow: var(--shadow-soft);
        }

        .symbol-select {
            min-width: 150px;
            border: 1px solid var(--border);
            border-radius: 8px;
            background: var(--surface-strong);
            color: var(--text);
            padding: 9px 11px;
            font: inherit;
            font-weight: 650;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.9);
        }

        .filter-input {
            width: 130px;
            border: 1px solid var(--border);
            border-radius: 8px;
            background: var(--surface-strong);
            color: var(--text);
            padding: 9px 11px;
            font: inherit;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.9);
        }

        .size-input {
            width: 110px;
            border: 1px solid var(--border);
            border-radius: 8px;
            background: var(--surface-strong);
            color: var(--text);
            padding: 9px 11px;
            font: inherit;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.9);
        }

        .connection-label {
            color: var(--muted);
            font-size: 12px;
            margin-bottom: 5px;
        }

        .connection-value {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 14px;
            font-weight: 700;
        }

        .dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--red);
        }

        .dot.live {
            background: var(--green);
        }

        .summary-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 12px;
            margin-bottom: 14px;
        }

        .panel {
            background: rgba(255,255,255,0.82);
            border: 1px solid var(--border);
            border-radius: 8px;
            box-shadow: var(--shadow);
            overflow: hidden;
        }

        .metric {
            padding: 18px;
        }

        .metric-label {
            color: var(--muted);
            font-size: 13px;
            margin-bottom: 8px;
        }

        .metric-value {
            font-size: 27px;
            line-height: 1.15;
            font-weight: 760;
        }

        .metric-help {
            margin-top: 7px;
            color: var(--muted-soft);
            font-size: 12px;
        }

        .positive {
            color: var(--green);
        }

        .negative {
            color: var(--red);
        }

        .content-grid {
            display: grid;
            grid-template-columns: minmax(0, 1.4fr) minmax(320px, 0.8fr);
            gap: 14px;
            align-items: start;
        }

        .panel-header {
            display: flex;
            justify-content: space-between;
            gap: 12px;
            padding: 16px 18px;
            border-bottom: 1px solid var(--border-soft);
        }

        .panel-title {
            font-size: 15px;
            font-weight: 750;
        }

        .panel-note {
            color: var(--muted);
            font-size: 12px;
        }

        table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
        }

        th,
        td {
            padding: 14px 18px;
            text-align: left;
            border-bottom: 1px solid var(--border-soft);
            font-size: 14px;
        }

        th {
            color: #536174;
            background: #f1f5f8;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            position: sticky;
            top: 0;
            z-index: 1;
        }

        th:first-child {
            border-top-left-radius: 8px;
        }

        th:last-child {
            border-top-right-radius: 8px;
        }

        tbody tr:nth-child(odd) {
            background: #ffffff;
        }

        tbody tr:nth-child(even) {
            background: #f6f8fa;
        }

        tbody tr {
            transition: background 0.15s ease, box-shadow 0.15s ease;
        }

        tbody tr:hover {
            background: #eef4f8;
            box-shadow: inset 3px 0 0 var(--blue);
        }

        tr:last-child td {
            border-bottom: 0;
        }

        .exchange {
            font-weight: 720;
        }

        .price {
            font-variant-numeric: tabular-nums;
            font-weight: 720;
        }

        .pill {
            display: inline-flex;
            align-items: center;
            gap: 7px;
            min-width: 72px;
            justify-content: center;
            padding: 5px 9px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 720;
            border: 1px solid transparent;
        }

        .pill.live {
            color: var(--green);
            background: var(--green-soft);
            border-color: #b7dfca;
        }

        .pill.stale {
            color: var(--red);
            background: var(--red-soft);
            border-color: #ecc2c2;
        }

        .opportunity-body {
            padding: 18px;
        }

        .route {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            margin-bottom: 14px;
        }

        .route-box {
            flex: 1;
            border: 1px solid var(--border);
            background: var(--surface);
            border-radius: 8px;
            padding: 12px;
        }

        .route-label {
            color: var(--muted);
            font-size: 12px;
            margin-bottom: 5px;
        }

        .route-value {
            font-size: 15px;
            font-weight: 750;
        }

        .arrow {
            color: var(--muted);
            font-weight: 700;
        }

        .facts {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px;
        }

        .history-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
            padding: 18px;
        }

        .execution-lab {
            display: grid;
            grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
            gap: 14px;
            padding: 0 18px 18px;
        }

        .verdict {
            border: 1px solid var(--border);
            border-radius: 8px;
            background: #f8fafc;
            padding: 14px;
        }

        .verdict-label {
            color: var(--muted);
            font-size: 12px;
            margin-bottom: 6px;
        }

        .verdict-value {
            font-size: 20px;
            font-weight: 780;
        }

        .verdict-detail {
            margin-top: 8px;
            color: var(--muted);
            font-size: 13px;
            line-height: 1.45;
        }

        .verdict.good {
            background: var(--green-soft);
            border-color: #b7dfca;
        }

        .verdict.risky {
            background: #fff4df;
            border-color: #efd8ad;
        }

        .verdict.bad {
            background: var(--red-soft);
            border-color: #ecc2c2;
        }

        .scenario-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 8px;
            margin-top: 12px;
        }

        .scenario-button {
            border: 1px solid var(--border);
            background: white;
            color: var(--text);
            border-radius: 8px;
            padding: 9px 10px;
            font: inherit;
            font-size: 13px;
            font-weight: 720;
            cursor: pointer;
            text-align: left;
        }

        .scenario-button.active {
            border-color: #afcbdc;
            background: var(--blue-soft);
            color: var(--blue);
        }

        .waterfall {
            display: grid;
            gap: 8px;
        }

        .waterfall-row {
            display: grid;
            grid-template-columns: 128px minmax(0, 1fr) 86px;
            gap: 10px;
            align-items: center;
            color: var(--muted);
            font-size: 12px;
        }

        .waterfall-track {
            height: 9px;
            border-radius: 999px;
            background: #e5ebf0;
            overflow: hidden;
        }

        .waterfall-fill {
            height: 100%;
            width: 0%;
            background: var(--blue);
            border-radius: 999px;
        }

        .waterfall-fill.positive {
            background: var(--green);
        }

        .waterfall-fill.negative {
            background: var(--red);
        }

        .book-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 14px;
            padding: 0 18px 18px;
        }

        .book-title {
            padding: 0 0 8px;
            color: var(--muted);
            font-size: 12px;
            font-weight: 720;
            text-transform: uppercase;
        }

        .fill-bar {
            height: 7px;
            min-width: 36px;
            border-radius: 999px;
            background: #e5ebf0;
            overflow: hidden;
        }

        .fill-bar span {
            display: block;
            height: 100%;
            width: 0%;
            background: var(--blue);
        }

        .fact {
            background: var(--surface);
            border: 1px solid var(--border-soft);
            border-radius: 8px;
            padding: 11px;
        }

        .ml-insight {
            margin-top: 14px;
            border: 1px solid var(--border);
            border-radius: 8px;
            background: linear-gradient(180deg, #ffffff, #f6f9fb);
            padding: 14px;
            box-shadow: var(--shadow-soft);
        }

        .ml-insight-header {
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            gap: 12px;
            margin-bottom: 10px;
        }

        .ml-title {
            font-size: 13px;
            font-weight: 780;
        }

        .ml-model {
            color: var(--muted);
            font-size: 11px;
        }

        .ml-scoreline {
            display: grid;
            grid-template-columns: 96px minmax(0, 1fr) 54px;
            gap: 9px;
            align-items: center;
            color: var(--muted);
            font-size: 12px;
            margin: 8px 0;
        }

        .ml-track {
            height: 8px;
            border-radius: 999px;
            background: #e5ebf0;
            overflow: hidden;
        }

        .ml-fill {
            display: block;
            height: 100%;
            width: 0%;
            background: var(--blue);
            border-radius: 999px;
        }

        .ml-risk-list {
            margin: 10px 0 0;
            padding: 0;
            list-style: none;
            display: grid;
            gap: 6px;
        }

        .ml-risk-list li {
            color: var(--muted);
            background: #eef2f5;
            border: 1px solid var(--border-soft);
            border-radius: 6px;
            padding: 7px 8px;
            font-size: 12px;
            line-height: 1.35;
        }

        .fact-label {
            color: var(--muted);
            font-size: 12px;
            margin-bottom: 5px;
        }

        .fact-value {
            font-size: 16px;
            font-weight: 730;
            font-variant-numeric: tabular-nums;
        }

        .warning {
            margin-top: 14px;
            color: var(--amber);
            background: #fff4df;
            border: 1px solid #efd8ad;
            border-radius: 8px;
            padding: 11px 12px;
            font-size: 13px;
            line-height: 1.4;
        }

        .footer {
            margin-top: 16px;
            color: var(--muted);
            font-size: 12px;
            display: flex;
            justify-content: space-between;
            gap: 12px;
        }

        @media (max-width: 900px) {
            body {
                padding: 18px;
            }

            .topbar,
            .toolbar,
            .content-grid,
            .summary-grid {
                grid-template-columns: 1fr;
                display: grid;
            }

            .connection {
                min-width: 0;
            }
        }

        @media (max-width: 560px) {
            h1 {
                font-size: 24px;
            }

            th,
            td {
                padding: 12px 10px;
                font-size: 13px;
            }

            .facts {
                grid-template-columns: 1fr;
            }

            .execution-lab,
            .book-grid,
            .scenario-grid {
                grid-template-columns: 1fr;
            }

            .waterfall-row {
                grid-template-columns: 1fr;
                gap: 5px;
            }

            .ml-scoreline {
                grid-template-columns: 1fr;
                gap: 5px;
            }

            .history-grid {
                grid-template-columns: 1fr;
            }

            .route {
                align-items: stretch;
                flex-direction: column;
            }

            .arrow {
                display: none;
            }
        }
    </style>
</head>
<body>
    <div class="language-modal" id="language-modal">
        <div class="language-card">
            <h2 data-i18n="languageTitle">Choose language / Выберите язык</h2>
            <p data-i18n="languageText">Select dashboard and documentation language.</p>
            <div class="language-choice">
                <button type="button" data-set-lang="en">English</button>
                <button type="button" data-set-lang="ru">Русский</button>
            </div>
        </div>
    </div>
    <main class="shell">
        <section class="topbar">
            <div>
                <div class="eyebrow" data-i18n="eyebrow">Market intelligence</div>
                <h1 data-i18n="title">Crypto Arbitrage Analytics</h1>
                <p class="subtitle" data-i18n="subtitle">
                    Real-time multi-symbol monitor across Binance, Bybit, OKX, and Gate.io.
                    The dashboard highlights bid/ask-based estimates, scoring, and stale data.
                </p>
            </div>
            <div class="top-actions">
                <div class="language-switch">
                    <button type="button" data-set-lang="en" id="lang-en">EN</button>
                    <button type="button" data-set-lang="ru" id="lang-ru">RU</button>
                </div>
                <div class="connection">
                    <div class="connection-label">WebSocket</div>
                    <div class="connection-value">
                        <span class="dot" id="ws-dot"></span>
                        <span id="ws-status" data-i18n="disconnected">Disconnected</span>
                    </div>
                </div>
            </div>
        </section>

        <section class="toolbar">
            <label for="symbol-select" class="panel-note" data-i18n="symbol">Symbol</label>
            <select id="symbol-select" class="symbol-select"></select>
            <label for="min-spread" class="panel-note" data-i18n="minSpread">Min spread %</label>
            <input id="min-spread" class="filter-input" type="number" min="0" step="0.01">
            <label for="execution-size" class="panel-note" data-i18n="executionSize">Execution size</label>
            <input id="execution-size" class="size-input" type="number" min="0.01" step="0.1" value="10">
            <a href="/docs/en" id="docs-link" class="panel-note">Docs</a>
        </section>

        <section class="summary-grid">
            <div class="panel metric">
                <div class="metric-label" data-i18n="bestSpread">Best spread</div>
                <div class="metric-value" id="spread">Waiting</div>
                <div class="metric-help" id="spread-route" data-i18n="noFreshRoute">No fresh route yet</div>
            </div>
            <div class="panel metric">
                <div class="metric-label" data-i18n="freshExchanges">Fresh exchanges</div>
                <div class="metric-value" id="fresh-count">0 / 4</div>
                <div class="metric-help" data-i18n="freshHelp">Only fresh prices are used for spread</div>
            </div>
            <div class="panel metric">
                <div class="metric-label" data-i18n="lastUpdate">Last update</div>
                <div class="metric-value" id="last-update">--</div>
                <div class="metric-help" data-i18n="localTime">Local dashboard time</div>
            </div>
        </section>

        <section class="panel" style="margin-top: 14px;">
            <div class="panel-header">
                <div>
                    <div class="panel-title" data-i18n="executionTitle">Order-book execution estimate</div>
                    <div class="panel-note" data-i18n="executionNote">Walks ask/bid levels and compares raw spread with executable net result</div>
                </div>
            </div>
            <div class="history-grid">
                <div class="fact">
                    <div class="fact-label" data-i18n="route">Route</div>
                    <div class="fact-value" id="exec-route">--</div>
                </div>
                <div class="fact">
                    <div class="fact-label" data-i18n="rawSpread">Raw spread</div>
                    <div class="fact-value" id="exec-raw">--</div>
                </div>
                <div class="fact">
                    <div class="fact-label" data-i18n="vwapSpread">VWAP spread</div>
                    <div class="fact-value" id="exec-vwap">--</div>
                </div>
                <div class="fact">
                    <div class="fact-label" data-i18n="netResult">Net result</div>
                    <div class="fact-value" id="exec-net">--</div>
                </div>
                <div class="fact">
                    <div class="fact-label" data-i18n="maxProfitableSize">Max profitable size</div>
                    <div class="fact-value" id="exec-max-size">--</div>
                </div>
                <div class="fact">
                    <div class="fact-label" data-i18n="snapshotSync">Snapshot sync</div>
                    <div class="fact-value" id="exec-sync">--</div>
                </div>
            </div>
            <div class="execution-lab">
                <div class="verdict" id="exec-verdict">
                    <div class="verdict-label" data-i18n="verdictLabel">Execution verdict</div>
                    <div class="verdict-value" id="exec-verdict-value">--</div>
                    <div class="verdict-detail" id="exec-verdict-detail">--</div>
                    <div class="scenario-grid">
                        <button class="scenario-button active" type="button" data-scenario="live" data-i18n="scenarioLive">Live market</button>
                        <button class="scenario-button" type="button" data-scenario="profitable" data-i18n="scenarioProfitable">Profitable</button>
                        <button class="scenario-button" type="button" data-scenario="slippage" data-i18n="scenarioSlippage">Slippage trap</button>
                        <button class="scenario-button" type="button" data-scenario="liquidity" data-i18n="scenarioLiquidity">Low liquidity</button>
                        <button class="scenario-button" type="button" data-scenario="stale" data-i18n="scenarioStale">Stale data</button>
                    </div>
                </div>
                <div class="waterfall">
                    <div class="waterfall-row">
                        <span data-i18n="rawSpread">Raw spread</span>
                        <div class="waterfall-track"><div class="waterfall-fill" id="bar-raw"></div></div>
                        <strong id="waterfall-raw">--</strong>
                    </div>
                    <div class="waterfall-row">
                        <span data-i18n="vwapSpread">VWAP spread</span>
                        <div class="waterfall-track"><div class="waterfall-fill" id="bar-vwap"></div></div>
                        <strong id="waterfall-vwap">--</strong>
                    </div>
                    <div class="waterfall-row">
                        <span data-i18n="feesImpact">Fees</span>
                        <div class="waterfall-track"><div class="waterfall-fill negative" id="bar-fees"></div></div>
                        <strong id="waterfall-fees">--</strong>
                    </div>
                    <div class="waterfall-row">
                        <span data-i18n="netResult">Net result</span>
                        <div class="waterfall-track"><div class="waterfall-fill" id="bar-net"></div></div>
                        <strong id="waterfall-net">--</strong>
                    </div>
                </div>
            </div>
            <div class="book-grid">
                <div>
                    <div class="book-title" id="buy-book-title" data-i18n="buyAsks">Buy asks</div>
                    <table>
                        <thead>
                            <tr>
                                <th data-i18n="price">Price</th>
                                <th data-i18n="filled">Filled</th>
                                <th data-i18n="depth">Depth</th>
                            </tr>
                        </thead>
                        <tbody id="buy-book-rows"></tbody>
                    </table>
                </div>
                <div>
                    <div class="book-title" id="sell-book-title" data-i18n="sellBids">Sell bids</div>
                    <table>
                        <thead>
                            <tr>
                                <th data-i18n="price">Price</th>
                                <th data-i18n="filled">Filled</th>
                                <th data-i18n="depth">Depth</th>
                            </tr>
                        </thead>
                        <tbody id="sell-book-rows"></tbody>
                    </table>
                </div>
            </div>
        </section>

        <section class="panel" style="margin-top: 14px;">
            <div class="panel-header">
                <div>
                    <div class="panel-title" data-i18n="historyTitle">History summary</div>
                    <div class="panel-note" data-i18n="historyNote">Signals saved in SQLite during the last hour</div>
                </div>
            </div>
            <div class="history-grid">
                <div class="fact">
                    <div class="fact-label" data-i18n="signals">Signals</div>
                    <div class="fact-value" id="history-count">--</div>
                </div>
                <div class="fact">
                    <div class="fact-label" data-i18n="maxSpread">Max spread</div>
                    <div class="fact-value" id="history-max-spread">--</div>
                </div>
                <div class="fact">
                    <div class="fact-label" data-i18n="avgSpread">Avg spread</div>
                    <div class="fact-value" id="history-avg-spread">--</div>
                </div>
                <div class="fact">
                    <div class="fact-label" data-i18n="maxNet">Max net</div>
                    <div class="fact-value" id="history-max-net">--</div>
                </div>
                <div class="fact">
                    <div class="fact-label" data-i18n="avgScore">Avg score</div>
                    <div class="fact-value" id="history-avg-score">--</div>
                </div>
            </div>
            <table>
                <thead>
                    <tr>
                        <th data-i18n="time">Time</th>
                        <th data-i18n="route">Route</th>
                        <th data-i18n="spread">Spread</th>
                        <th data-i18n="net">Net</th>
                        <th data-i18n="score">Score</th>
                    </tr>
                </thead>
                <tbody id="recent-opportunities"></tbody>
            </table>
        </section>

        <section class="content-grid">
            <div class="panel">
                <div class="panel-header">
                    <div>
                        <div class="panel-title" data-i18n="pricesTitle">Exchange prices</div>
                        <div class="panel-note" data-i18n="pricesNote">Top-of-book bid/ask from public streams</div>
                    </div>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th data-i18n="exchange">Exchange</th>
                            <th data-i18n="bid">Bid</th>
                            <th data-i18n="ask">Ask</th>
                            <th data-i18n="age">Age</th>
                            <th data-i18n="status">Status</th>
                        </tr>
                    </thead>
                    <tbody id="exchange-rows"></tbody>
                </table>
            </div>

            <aside class="panel">
                <div class="panel-header">
                    <div>
                        <div class="panel-title" data-i18n="opportunityTitle">Estimated opportunity</div>
                        <div class="panel-note" data-i18n="opportunityNote">Simple fee-aware calculation</div>
                    </div>
                </div>
                <div class="opportunity-body">
                    <div class="route">
                        <div class="route-box">
                            <div class="route-label" data-i18n="buyOn">Buy on</div>
                            <div class="route-value" id="buy-on">--</div>
                        </div>
                        <div class="arrow" data-i18n="to">to</div>
                        <div class="route-box">
                            <div class="route-label" data-i18n="sellOn">Sell on</div>
                            <div class="route-value" id="sell-on">--</div>
                        </div>
                    </div>

                    <div class="facts">
                        <div class="fact">
                            <div class="fact-label" data-i18n="grossPnl">Gross PnL</div>
                            <div class="fact-value" id="gross-pnl">--</div>
                        </div>
                        <div class="fact">
                            <div class="fact-label" data-i18n="feesImpact">Fees</div>
                            <div class="fact-value" id="fees">--</div>
                        </div>
                        <div class="fact">
                            <div class="fact-label" data-i18n="netEstimate">Net estimate</div>
                            <div class="fact-value" id="net-pnl">--</div>
                        </div>
                        <div class="fact">
                            <div class="fact-label" data-i18n="spread">Spread</div>
                            <div class="fact-value" id="spread-pct">--</div>
                        </div>
                        <div class="fact">
                            <div class="fact-label" data-i18n="score">Score</div>
                            <div class="fact-value" id="score">--</div>
                        </div>
                        <div class="fact">
                            <div class="fact-label" data-i18n="mlQuality">ML quality</div>
                            <div class="fact-value" id="quality">--</div>
                        </div>
                    </div>

                    <div class="ml-insight">
                        <div class="ml-insight-header">
                            <div>
                                <div class="ml-title" data-i18n="mlSignalAnalysis">ML signal analysis</div>
                                <div class="ml-model" id="ml-model">--</div>
                            </div>
                            <div class="pill" id="ml-recommendation">--</div>
                        </div>
                        <div class="ml-scoreline">
                            <span data-i18n="probability">Probability</span>
                            <div class="ml-track"><span class="ml-fill" id="ml-probability-bar"></span></div>
                            <strong id="ml-probability">--</strong>
                        </div>
                        <div class="ml-scoreline">
                            <span data-i18n="confidence">Confidence</span>
                            <div class="ml-track"><span class="ml-fill" id="ml-confidence-bar"></span></div>
                            <strong id="ml-confidence">--</strong>
                        </div>
                        <ul class="ml-risk-list" id="ml-risk-list"></ul>
                    </div>

                    <div class="warning" data-i18n="topBookWarning">
                        Estimate uses top-of-book bid/ask. Real execution still needs deeper order-book simulation, slippage, and transfer costs.
                    </div>
                </div>
            </aside>
        </section>

        <div class="footer">
            <span data-i18n="localDashboard">Local analytical dashboard</span>
            <span data-i18n="apiFooter">API: /api/health /api/prices /api/opportunity</span>
        </div>
    </main>

    <script>
        const SYMBOLS = __SYMBOLS__;
        let selectedSymbol = __DEFAULT_SYMBOL__;
        let minSpreadPct = __MIN_SPREAD_PCT__;
        let executionSize = 10;
        let language = localStorage.getItem('dashboardLanguage') || 'en';

        const TRANSLATIONS = {
            en: {
                languageTitle: 'Choose language / Выберите язык',
                languageText: 'Select dashboard and documentation language.',
                eyebrow: 'Market intelligence',
                title: 'Crypto Arbitrage Analytics',
                subtitle: 'Real-time multi-symbol monitor across Binance, Bybit, OKX, and Gate.io. The dashboard highlights bid/ask-based estimates, scoring, and stale data.',
                symbol: 'Symbol',
                minSpread: 'Min spread %',
                executionSize: 'Execution size',
                docs: 'Docs',
                bestSpread: 'Best spread',
                freshExchanges: 'Fresh exchanges',
                freshHelp: 'Only fresh prices are used for spread',
                lastUpdate: 'Last update',
                localTime: 'Local dashboard time',
                executionTitle: 'Order-book execution estimate',
                executionNote: 'Walks ask/bid levels and compares raw spread with executable net result',
                verdictLabel: 'Execution verdict',
                route: 'Route',
                rawSpread: 'Raw spread',
                vwapSpread: 'VWAP spread',
                feesImpact: 'Fees',
                netResult: 'Net result',
                maxProfitableSize: 'Max profitable size',
                snapshotSync: 'Snapshot sync',
                scenarioLive: 'Live market',
                scenarioProfitable: 'Profitable',
                scenarioSlippage: 'Slippage trap',
                scenarioLiquidity: 'Low liquidity',
                scenarioStale: 'Stale data',
                buyAsks: 'Buy asks',
                sellBids: 'Sell bids',
                price: 'Price',
                filled: 'Filled',
                depth: 'Depth',
                historyTitle: 'History summary',
                historyNote: 'Signals saved in SQLite during the last hour',
                signals: 'Signals',
                maxSpread: 'Max spread',
                avgSpread: 'Avg spread',
                maxNet: 'Max net',
                avgScore: 'Avg score',
                time: 'Time',
                spread: 'Spread',
                net: 'Net',
                score: 'Score',
                pricesTitle: 'Exchange prices',
                pricesNote: 'Top-of-book bid/ask from public streams',
                exchange: 'Exchange',
                bid: 'Bid',
                ask: 'Ask',
                age: 'Age',
                status: 'Status',
                opportunityTitle: 'Estimated opportunity',
                opportunityNote: 'Simple fee-aware calculation',
                buyOn: 'Buy on',
                sellOn: 'Sell on',
                grossPnl: 'Gross PnL',
                netEstimate: 'Net estimate',
                mlQuality: 'ML quality',
                mlSignalAnalysis: 'ML signal analysis',
                probability: 'Probability',
                confidence: 'Confidence',
                topBookWarning: 'Estimate uses top-of-book bid/ask. Real execution still needs deeper order-book simulation, slippage, and transfer costs.',
                localDashboard: 'Local analytical dashboard',
                apiFooter: 'API: /api/health /api/prices /api/opportunity',
                waiting: 'Waiting',
                connected: 'Connected',
                disconnected: 'Disconnected',
                noFreshRoute: 'No fresh route yet',
                live: 'Live',
                stale: 'Stale',
                filtered: 'Filtered',
                belowThreshold: 'Below threshold',
                executable: 'Executable',
                risky: 'Risky',
                rejected: 'Rejected',
                noExecution: 'No executable route for the selected size.',
                buyAsksOn: 'Buy asks on',
                sellBidsOn: 'Sell bids on',
                scoreLabel: 'Score',
                fillLabel: 'Fill',
                slippageLabel: 'Slippage',
                snapshotSkewLabel: 'Snapshot skew',
                ms: 'ms',
                recommendation_show_to_user: 'show to user',
                recommendation_watch: 'watch',
                recommendation_ignore: 'ignore',
                recommendation_wait_for_data: 'wait for data',
                quality_strong: 'strong',
                quality_watch: 'watch',
                quality_weak: 'weak',
                quality_no_signal: 'no signal',
                risk_net_result: 'net result is not positive after fees',
                risk_fees: 'fees consume a large part of gross spread',
                risk_unknown_liquidity: 'visible liquidity size is unknown',
                risk_small_liquidity: 'visible liquidity is small',
                risk_narrow_spread: 'spread is too narrow',
                risk_no_major: 'no major top-of-book risk detected',
                reason_net_positive: 'net profit remains positive after fees and depth simulation',
                reason_net_negative: 'net profit is not positive after fees and depth simulation',
                reason_vwap_positive: 'VWAP sell price is above VWAP buy price',
                reason_full_fill: 'target size is fully executable on visible levels',
                reason_not_full_fill: 'target size is not fully executable on visible levels',
                reason_slippage_low: 'combined slippage is low',
                reason_slippage_moderate: 'combined slippage is moderate',
                reason_slippage_high: 'combined slippage is high',
                reason_few_levels: 'execution uses only a few order-book levels',
                rejectedLiquidity: 'Rejected: visible order-book depth cannot fill the selected size on both sides.',
                rejectedStale: 'Rejected: order-book snapshots are older than the allowed freshness window.',
                to: 'to',
            },
            ru: {
                languageTitle: 'Выберите язык',
                languageText: 'Выберите язык dashboard и документации.',
                eyebrow: 'Аналитика рынка',
                title: 'Crypto Arbitrage Analytics',
                subtitle: 'Мониторинг нескольких монет в реальном времени на Binance, Bybit, OKX и Gate.io. Dashboard показывает оценки по bid/ask, score и устаревшие данные.',
                symbol: 'Монета',
                minSpread: 'Мин. спред %',
                executionSize: 'Объем сделки',
                docs: 'Документация',
                bestSpread: 'Лучший спред',
                freshExchanges: 'Свежие биржи',
                freshHelp: 'Для спреда используются только свежие цены',
                lastUpdate: 'Последнее обновление',
                localTime: 'Локальное время dashboard',
                executionTitle: 'Оценка исполнения по стаканам',
                executionNote: 'Проходит по уровням ask/bid и сравнивает сырой спред с чистым результатом',
                verdictLabel: 'Вердикт исполнения',
                route: 'Маршрут',
                rawSpread: 'Сырой спред',
                vwapSpread: 'VWAP-спред',
                feesImpact: 'Комиссии',
                netResult: 'Чистый результат',
                maxProfitableSize: 'Макс. прибыльный объем',
                snapshotSync: 'Синхронизация стаканов',
                scenarioLive: 'Текущий рынок',
                scenarioProfitable: 'Прибыльный',
                scenarioSlippage: 'Ловушка проскальзывания',
                scenarioLiquidity: 'Мало ликвидности',
                scenarioStale: 'Старые данные',
                buyAsks: 'Покупка по ask',
                sellBids: 'Продажа по bid',
                price: 'Цена',
                filled: 'Заполнено',
                depth: 'Глубина',
                historyTitle: 'История сигналов',
                historyNote: 'Сигналы, сохраненные в SQLite за последний час',
                signals: 'Сигналы',
                maxSpread: 'Макс. спред',
                avgSpread: 'Средний спред',
                maxNet: 'Макс. чистая прибыль',
                avgScore: 'Средний score',
                time: 'Время',
                spread: 'Спред',
                net: 'Чистый результат',
                score: 'Score',
                pricesTitle: 'Цены на биржах',
                pricesNote: 'Лучшие bid/ask из публичных потоков',
                exchange: 'Биржа',
                bid: 'Bid',
                ask: 'Ask',
                age: 'Возраст',
                status: 'Статус',
                opportunityTitle: 'Оценка возможности',
                opportunityNote: 'Простой расчет с учетом комиссий',
                buyOn: 'Купить на',
                sellOn: 'Продать на',
                grossPnl: 'Грязная прибыль',
                netEstimate: 'Чистая оценка',
                mlQuality: 'ML-качество',
                mlSignalAnalysis: 'ML-анализ сигнала',
                probability: 'Вероятность',
                confidence: 'Уверенность',
                topBookWarning: 'Оценка использует лучший bid/ask. Реальное исполнение требует проверки глубины стакана, проскальзывания и затрат на перевод.',
                localDashboard: 'Локальный аналитический dashboard',
                apiFooter: 'API: /api/health /api/prices /api/opportunity',
                waiting: 'Ожидание',
                connected: 'Подключено',
                disconnected: 'Отключено',
                noFreshRoute: 'Свежего маршрута пока нет',
                live: 'Актуально',
                stale: 'Устарело',
                filtered: 'Отфильтровано',
                belowThreshold: 'Ниже порога',
                executable: 'Исполнимо',
                risky: 'Рискованно',
                rejected: 'Отклонено',
                noExecution: 'Нет исполнимого маршрута для выбранного объема.',
                buyAsksOn: 'Покупка по ask на',
                sellBidsOn: 'Продажа по bid на',
                scoreLabel: 'Score',
                fillLabel: 'Заполнение',
                slippageLabel: 'Проскальзывание',
                snapshotSkewLabel: 'Рассинхрон стаканов',
                ms: 'мс',
                recommendation_show_to_user: 'показать пользователю',
                recommendation_watch: 'наблюдать',
                recommendation_ignore: 'игнорировать',
                recommendation_wait_for_data: 'ждать данные',
                quality_strong: 'сильный',
                quality_watch: 'наблюдать',
                quality_weak: 'слабый',
                quality_no_signal: 'нет сигнала',
                risk_net_result: 'чистый результат неположительный после комиссий',
                risk_fees: 'комиссии съедают большую часть грязного спреда',
                risk_unknown_liquidity: 'объем видимой ликвидности неизвестен',
                risk_small_liquidity: 'видимая ликвидность маленькая',
                risk_narrow_spread: 'спред слишком узкий',
                risk_no_major: 'серьезных top-of-book рисков не найдено',
                reason_net_positive: 'чистая прибыль остается положительной после комиссий и симуляции стакана',
                reason_net_negative: 'чистая прибыль неположительная после комиссий и симуляции стакана',
                reason_vwap_positive: 'VWAP-цена продажи выше VWAP-цены покупки',
                reason_full_fill: 'целевой объем полностью исполним на видимых уровнях',
                reason_not_full_fill: 'целевой объем не исполним полностью на видимых уровнях',
                reason_slippage_low: 'общее проскальзывание низкое',
                reason_slippage_moderate: 'общее проскальзывание умеренное',
                reason_slippage_high: 'общее проскальзывание высокое',
                reason_few_levels: 'исполнение использует только несколько уровней стакана',
                rejectedLiquidity: 'Отклонено: видимой глубины стакана недостаточно для выбранного объема с обеих сторон.',
                rejectedStale: 'Отклонено: снимки стаканов старше допустимого окна свежести.',
                to: 'в',
            },
        };

        const t = (key) => TRANSLATIONS[language][key] || TRANSLATIONS.en[key] || key;
        const translateQuality = (value) => t('quality_' + value) || value || '--';
        const translateRecommendation = (value) => t('recommendation_' + value) || value || '--';
        const translateRisk = (risk) => {
            const riskMap = {
                'net result is not positive after fees': 'risk_net_result',
                'fees consume a large part of gross spread': 'risk_fees',
                'visible liquidity size is unknown': 'risk_unknown_liquidity',
                'visible liquidity is small': 'risk_small_liquidity',
                'spread is too narrow': 'risk_narrow_spread',
                'no major top-of-book risk detected': 'risk_no_major',
            };
            return riskMap[risk] ? t(riskMap[risk]) : risk;
        };
        const translateReason = (reason) => {
            const reasonMap = {
                'net profit remains positive after fees and depth simulation': 'reason_net_positive',
                'net profit is not positive after fees and depth simulation': 'reason_net_negative',
                'VWAP sell price is above VWAP buy price': 'reason_vwap_positive',
                'target size is fully executable on visible levels': 'reason_full_fill',
                'target size is not fully executable on visible levels': 'reason_not_full_fill',
                'combined slippage is low': 'reason_slippage_low',
                'combined slippage is moderate': 'reason_slippage_moderate',
                'combined slippage is high': 'reason_slippage_high',
                'execution uses only a few order-book levels': 'reason_few_levels',
            };
            return reasonMap[reason] ? t(reasonMap[reason]) : reason;
        };
        const translateExecutionNote = (note) => {
            if (!note) {
                return t('noExecution');
            }
            if (note.startsWith('Rejected: visible order-book depth')) {
                return t('rejectedLiquidity');
            }
            if (note.startsWith('Rejected: order-book snapshots')) {
                return t('rejectedStale');
            }
            return note;
        };

        const applyLanguage = (nextLanguage, persist = true, closeModal = true) => {
            language = nextLanguage;
            if (persist) {
                localStorage.setItem('dashboardLanguage', language);
            }
            document.documentElement.lang = language;
            document.querySelectorAll('[data-i18n]').forEach((node) => {
                node.textContent = t(node.dataset.i18n);
            });
            document.getElementById('docs-link').textContent = t('docs');
            document.getElementById('docs-link').href = language === 'ru' ? '/docs/ru' : '/docs/en';
            document.getElementById('lang-en').classList.toggle('active', language === 'en');
            document.getElementById('lang-ru').classList.toggle('active', language === 'ru');
            updateScenarioButtons();
            if (closeModal) {
                document.getElementById('language-modal').classList.remove('open');
            }
        };

        const formatPrice = (value) => value === null || value === undefined
            ? t('waiting')
            : '$' + value.toFixed(2);

        const formatMoney = (value) => value === null || value === undefined
            ? '--'
            : (value >= 0 ? '+$' : '-$') + Math.abs(value).toFixed(2);

        const symbolSelect = document.getElementById('symbol-select');
        document.querySelectorAll('[data-set-lang]').forEach((button) => {
            button.addEventListener('click', () => applyLanguage(button.dataset.setLang));
        });
        if (!localStorage.getItem('dashboardLanguage')) {
            document.getElementById('language-modal').classList.add('open');
        }

        for (const symbol of SYMBOLS) {
            const option = document.createElement('option');
            option.value = symbol;
            option.textContent = symbol;
            if (symbol === selectedSymbol) {
                option.selected = true;
            }
            symbolSelect.appendChild(option);
        }
        symbolSelect.addEventListener('change', () => {
            selectedSymbol = symbolSelect.value;
            resetOpportunity();
            updateHistory();
        });

        const minSpreadInput = document.getElementById('min-spread');
        minSpreadInput.value = minSpreadPct;
        minSpreadInput.addEventListener('input', () => {
            minSpreadPct = Number(minSpreadInput.value || 0);
        });
        const executionSizeInput = document.getElementById('execution-size');
        executionSizeInput.addEventListener('input', () => {
            executionSize = Number(executionSizeInput.value || 10);
            executionScenario = 'live';
            updateScenarioButtons();
        });

        let executionScenario = 'live';
        const scenarioSizes = {
            live: 10,
            profitable: 10,
            slippage: 20,
            liquidity: 10,
            stale: 10,
        };
        const updateScenarioButtons = () => {
            document.querySelectorAll('[data-scenario]').forEach((button) => {
                button.classList.toggle('active', button.dataset.scenario === executionScenario);
                if (button.dataset.i18n) {
                    button.textContent = t(button.dataset.i18n);
                }
            });
        };
        document.querySelectorAll('[data-scenario]').forEach((button) => {
            button.addEventListener('click', () => {
                executionScenario = button.dataset.scenario;
                executionSize = scenarioSizes[executionScenario] || 10;
                executionSizeInput.value = executionSize;
                updateScenarioButtons();
                updateExecution();
            });
        });
        applyLanguage(language, false, false);

        const resetOpportunity = () => {
            document.getElementById('buy-on').textContent = '--';
            document.getElementById('sell-on').textContent = '--';
            document.getElementById('gross-pnl').textContent = '--';
            document.getElementById('fees').textContent = '--';
            document.getElementById('net-pnl').textContent = '--';
            document.getElementById('spread-pct').textContent = '--';
            document.getElementById('score').textContent = '--';
            document.getElementById('quality').textContent = '--';
            renderMlInsight(null);
        };

        const renderMlInsight = (quality) => {
            const probability = quality ? quality.probability || 0 : 0;
            const confidence = quality ? quality.confidence || 0 : 0;
            document.getElementById('ml-model').textContent = quality ? quality.model : '--';
            document.getElementById('ml-probability').textContent = quality ? Math.round(probability * 100) + '%' : '--';
            document.getElementById('ml-confidence').textContent = quality ? Math.round(confidence * 100) + '%' : '--';
            document.getElementById('ml-probability-bar').style.width = Math.round(probability * 100) + '%';
            document.getElementById('ml-confidence-bar').style.width = Math.round(confidence * 100) + '%';

            const recommendation = document.getElementById('ml-recommendation');
            recommendation.textContent = quality ? translateRecommendation(quality.recommendation) : '--';
            recommendation.className = 'pill ' + (quality && quality.quality === 'strong' ? 'live' : 'stale');

            const list = document.getElementById('ml-risk-list');
            list.innerHTML = '';
            const risks = quality ? quality.risk_factors || [] : [];
            for (const risk of risks.slice(0, 4)) {
                const item = document.createElement('li');
                item.textContent = translateRisk(risk);
                list.appendChild(item);
            }
        };

        const renderRows = (exchanges) => {
            const tbody = document.getElementById('exchange-rows');
            tbody.innerHTML = '';

            for (const [exchange, item] of Object.entries(exchanges)) {
                const live = item && item.live;
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td class="exchange">${exchange}</td>
                    <td class="price">${item ? formatPrice(item.bid_price) : t('waiting')}</td>
                    <td class="price">${item ? formatPrice(item.ask_price) : t('waiting')}</td>
                    <td>${item ? item.age : '--'}</td>
                    <td><span class="pill ${live ? 'live' : 'stale'}">${live ? t('live') : t('stale')}</span></td>
                `;
                tbody.appendChild(row);
            }
        };

        const percentText = (value) => value === null || value === undefined ? '--' : value.toFixed(4) + '%';

        const setBar = (id, value, maxValue) => {
            const element = document.getElementById(id);
            const width = maxValue > 0 ? Math.min(100, Math.abs(value) / maxValue * 100) : 0;
            element.style.width = width + '%';
            element.className = 'waterfall-fill ' + (value >= 0 ? 'positive' : 'negative');
        };

        const renderFillRows = (targetId, fills) => {
            const tbody = document.getElementById(targetId);
            tbody.innerHTML = '';
            if (!fills || fills.length === 0) {
                const row = document.createElement('tr');
                row.innerHTML = '<td>--</td><td>--</td><td>--</td>';
                tbody.appendChild(row);
                return;
            }
            for (const fill of fills) {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td class="price">$${fill.price.toFixed(4)}</td>
                    <td>${fill.filled_size.toFixed(4)} / ${fill.available_size.toFixed(4)}</td>
                    <td>
                        <div class="fill-bar">
                            <span style="width: ${Math.min(100, fill.fill_pct).toFixed(1)}%"></span>
                        </div>
                    </td>
                `;
                tbody.appendChild(row);
            }
        };

        const resetExecution = (detail) => {
            document.getElementById('exec-route').textContent = '--';
            document.getElementById('exec-raw').textContent = '--';
            document.getElementById('exec-vwap').textContent = '--';
            document.getElementById('exec-net').textContent = '--';
            document.getElementById('exec-max-size').textContent = '--';
            document.getElementById('exec-sync').textContent = '--';
            document.getElementById('waterfall-raw').textContent = '--';
            document.getElementById('waterfall-vwap').textContent = '--';
            document.getElementById('waterfall-fees').textContent = '--';
            document.getElementById('waterfall-net').textContent = '--';
            setBar('bar-raw', 0, 1);
            setBar('bar-vwap', 0, 1);
            setBar('bar-fees', 0, 1);
            setBar('bar-net', 0, 1);
            renderFillRows('buy-book-rows', []);
            renderFillRows('sell-book-rows', []);
            const verdict = document.getElementById('exec-verdict');
            verdict.className = 'verdict bad';
            document.getElementById('exec-verdict-value').textContent = t('rejected');
            document.getElementById('exec-verdict-detail').textContent = translateExecutionNote(detail);
        };

        const updateOpportunity = async () => {
            try {
                const response = await fetch('/api/opportunity?symbol=' + encodeURIComponent(selectedSymbol));
                const payload = await response.json();
                const item = payload.opportunity;
                const quality = payload.quality;

                if (!item) {
                    resetOpportunity();
                    return;
                }

                if (Math.abs(item.spread_pct) < minSpreadPct) {
                    resetOpportunity();
                    document.getElementById('buy-on').textContent = t('filtered');
                    document.getElementById('sell-on').textContent = t('belowThreshold');
                    return;
                }

                document.getElementById('buy-on').textContent = item.buy_on;
                document.getElementById('sell-on').textContent = item.sell_on;
                document.getElementById('gross-pnl').textContent = formatMoney(item.gross_profit_usd);
                document.getElementById('fees').textContent = '$' + item.estimated_fees_usd.toFixed(2);

                const net = document.getElementById('net-pnl');
                net.textContent = formatMoney(item.estimated_net_profit_usd);
                net.className = 'fact-value ' + (item.estimated_net_profit_usd >= 0 ? 'positive' : 'negative');

                document.getElementById('spread-pct').textContent = item.spread_pct.toFixed(3) + '%';
                document.getElementById('score').textContent = item.score.toFixed(1) + ' / 100';
                document.getElementById('quality').textContent = quality ? translateQuality(quality.quality) : '--';
                renderMlInsight(quality);
            } catch (error) {
                console.error('Failed to load opportunity', error);
            }
        };

        const updateHistory = async () => {
            try {
                const [historyResponse, opportunitiesResponse] = await Promise.all([
                    fetch('/api/history?symbol=' + encodeURIComponent(selectedSymbol)),
                    fetch('/api/opportunities?symbol=' + encodeURIComponent(selectedSymbol) + '&limit=8')
                ]);
                const item = await historyResponse.json();
                const opportunities = await opportunitiesResponse.json();
                document.getElementById('history-count').textContent = item.opportunity_count ?? 0;
                document.getElementById('history-max-spread').textContent =
                    item.max_spread_pct === null || item.max_spread_pct === undefined ? '--' : item.max_spread_pct.toFixed(4) + '%';
                document.getElementById('history-avg-spread').textContent =
                    item.avg_spread_pct === null || item.avg_spread_pct === undefined ? '--' : item.avg_spread_pct.toFixed(4) + '%';
                document.getElementById('history-max-net').textContent =
                    item.max_net_profit_usd === null || item.max_net_profit_usd === undefined ? '--' : formatMoney(item.max_net_profit_usd);
                document.getElementById('history-avg-score').textContent =
                    item.avg_score === null || item.avg_score === undefined ? '--' : item.avg_score.toFixed(1);

                const tbody = document.getElementById('recent-opportunities');
                tbody.innerHTML = '';
                for (const row of opportunities.opportunities || []) {
                    const tr = document.createElement('tr');
                    const time = new Date(row.ts * 1000).toLocaleTimeString();
                    tr.innerHTML = `
                        <td>${time}</td>
                        <td>${row.buy_on} ${t('to')} ${row.sell_on}</td>
                        <td>${row.spread_pct.toFixed(4)}%</td>
                        <td>${formatMoney(row.estimated_net_profit_usd)}</td>
                        <td>${row.score.toFixed(1)}</td>
                    `;
                    tbody.appendChild(tr);
                }
            } catch (error) {
                console.error('Failed to load history', error);
            }
        };

        const updateExecution = async () => {
            try {
                const response = await fetch(
                    '/api/execution?symbol=' + encodeURIComponent(selectedSymbol) +
                    '&size=' + encodeURIComponent(executionSize) +
                    '&scenario=' + encodeURIComponent(executionScenario)
                );
                const payload = await response.json();
                const item = payload.execution;
                if (!item) {
                    resetExecution(payload.note);
                    return;
                }
                document.getElementById('exec-route').textContent = item.buy_on + ' ' + t('to') + ' ' + item.sell_on;
                document.getElementById('exec-raw').textContent = percentText(item.raw_spread_pct);
                document.getElementById('exec-vwap').textContent = percentText(item.executable_spread_pct);
                const net = document.getElementById('exec-net');
                net.textContent = formatMoney(item.estimated_net_profit_usd);
                net.className = 'fact-value ' + (item.estimated_net_profit_usd >= 0 ? 'positive' : 'negative');
                document.getElementById('exec-max-size').textContent = item.max_profitable_size.toFixed(4);
                document.getElementById('exec-sync').textContent =
                    item.sync_quality + ' / ' + item.snapshot_skew_ms.toFixed(1) + ' ms';
                document.getElementById('waterfall-raw').textContent = percentText(item.raw_spread_pct);
                document.getElementById('waterfall-vwap').textContent = percentText(item.executable_spread_pct);
                document.getElementById('waterfall-fees').textContent = '-$' + item.estimated_fees_usd.toFixed(2);
                document.getElementById('waterfall-net').textContent = formatMoney(item.estimated_net_profit_usd);
                const maxBar = Math.max(
                    Math.abs(item.raw_spread_pct),
                    Math.abs(item.executable_spread_pct),
                    Math.abs(item.estimated_net_profit_usd / Math.max(1, item.buy_notional_usd) * 100),
                    0.01
                );
                setBar('bar-raw', item.raw_spread_pct, maxBar);
                setBar('bar-vwap', item.executable_spread_pct, maxBar);
                setBar('bar-fees', -item.estimated_fees_usd / Math.max(1, item.buy_notional_usd) * 100, maxBar);
                setBar('bar-net', item.estimated_net_profit_usd / Math.max(1, item.buy_notional_usd) * 100, maxBar);
                renderFillRows('buy-book-rows', item.buy_fills);
                renderFillRows('sell-book-rows', item.sell_fills);
                document.getElementById('buy-book-title').textContent = t('buyAsksOn') + ' ' + item.buy_on;
                document.getElementById('sell-book-title').textContent = t('sellBidsOn') + ' ' + item.sell_on;
                const verdict = document.getElementById('exec-verdict');
                const good = item.estimated_net_profit_usd > 0 && item.fill_ratio >= 1 && item.combined_slippage_pct < 0.2;
                const risky = item.estimated_net_profit_usd > 0 && item.fill_ratio >= 1;
                verdict.className = 'verdict ' + (good ? 'good' : risky ? 'risky' : 'bad');
                document.getElementById('exec-verdict-value').textContent = good ? t('executable') : risky ? t('risky') : t('rejected');
                document.getElementById('exec-verdict-detail').textContent =
                    t('scoreLabel') + ' ' + item.score.toFixed(1) + '/100. ' +
                    t('fillLabel') + ' ' + (item.fill_ratio * 100).toFixed(1) + '%. ' +
                    t('slippageLabel') + ' ' + item.combined_slippage_pct.toFixed(4) + '%. ' +
                    t('snapshotSkewLabel') + ' ' + item.snapshot_skew_ms.toFixed(1) + ' ' + t('ms') + '. ' +
                    (item.score_reasons || []).slice(0, 2).map(translateReason).join(' ');
            } catch (error) {
                console.error('Failed to load execution estimate', error);
            }
        };

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const ws = new WebSocket(protocol + '//' + window.location.host + '/ws');

        ws.onopen = () => {
            document.getElementById('ws-status').textContent = t('connected');
            document.getElementById('ws-dot').className = 'dot live';
        };

        ws.onclose = () => {
            document.getElementById('ws-status').textContent = t('disconnected');
            document.getElementById('ws-dot').className = 'dot';
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            const symbolData = data.symbols[selectedSymbol];
            if (!symbolData) {
                return;
            }

            renderRows(symbolData.exchanges);

            const spreadEl = document.getElementById('spread');
            if (symbolData.spread !== null) {
                spreadEl.textContent = (symbolData.spread > 0 ? '+$' : '-$') + Math.abs(symbolData.spread).toFixed(2);
                spreadEl.className = 'metric-value ' + (symbolData.spread > 0 ? 'positive' : 'negative');
                document.getElementById('spread-route').textContent = symbolData.route;
            } else {
                spreadEl.textContent = t('waiting');
                spreadEl.className = 'metric-value';
                document.getElementById('spread-route').textContent = t('noFreshRoute');
            }

            document.getElementById('fresh-count').textContent = symbolData.fresh_count + ' / ' + symbolData.exchange_count;
            document.getElementById('last-update').textContent = data.time;
            updateOpportunity();
            updateHistory();
            updateExecution();
        };
    </script>
</body>
</html>
        """
        html = html.replace("__SYMBOLS__", json.dumps(list(self.symbols)))
        html = html.replace("__DEFAULT_SYMBOL__", json.dumps(self.symbol))
        html = html.replace("__MIN_SPREAD_PCT__", json.dumps(self.min_spread_pct))
        return web.Response(text=html, content_type='text/html')

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
