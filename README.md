# Crypto Arbitrage Analytics

Real-time analytical monitor for possible crypto market anomalies across Binance, Bybit, OKX, and Gate.io.

The project supports multiple symbols, for example `SOLUSDT`, `BTCUSDT`, and `ETHUSDT`.

Important: this is not a guaranteed-profit trading bot. It is an educational backend project and an analytical tool. It helps detect suspicious price and funding differences, but real trading also requires deeper order-book simulation, liquidity checks, slippage, transfer time, exchange limits, and risk controls.

## Main Algorithmic Feature

The central technical feature is realistic execution estimation using order-book depth.

Instead of only comparing:

```text
best bid - best ask
```

the project can:

- fetch order-book snapshots;
- simulate buying a target size through ask levels;
- simulate selling the same size through bid levels;
- calculate VWAP buy and sell prices;
- subtract taker fees;
- calculate slippage;
- estimate maximum profitable size;
- score the signal quality;
- show the difference between raw spread and executable net result.

Detailed explanation: [EXECUTION_ALGORITHM.md](EXECUTION_ALGORITHM.md)

The dashboard includes defense-ready execution scenarios:

- `Profitable` shows a clean executable opportunity.
- `Slippage trap` shows a raw spread that becomes unattractive after walking the book.
- `Low liquidity` shows rejection when visible depth cannot fill the selected size.
- `Stale data` shows rejection when snapshots are too old.

The execution estimator also reports snapshot synchronization quality:

- `snapshot_skew_ms` shows the timestamp difference between the buy-side and sell-side order books.
- `sync_quality` marks the route as `fresh`, `acceptable`, or `weak`.
- routes with excessive snapshot skew are rejected instead of being presented as reliable signals.

## What the App Does

- connects to public exchange WebSocket streams;
- receives top-of-book bid/ask market data;
- stores the latest market snapshot from each exchange in memory;
- supports several trading symbols;
- estimates the largest bid/ask cross-exchange spread;
- subtracts a simple taker-fee estimate;
- calculates an opportunity score;
- stores snapshots and opportunities in SQLite;
- includes an ML-ready baseline quality model;
- supports a clearly marked offline demo mode;
- estimates realistic execution through visible order-book levels;
- checks funding rates through public REST APIs;
- shows a terminal dashboard;
- serves a browser dashboard;
- exposes JSON API endpoints;
- exposes a FastAPI/OpenAPI app for Swagger documentation;
- optionally sends Telegram notifications and handles Telegram commands.

## Architecture

```text
Exchange WebSockets -> exchange adapters -> MarketSnapshot -> MarketDataState
                                                             -> analytics/scoring
                                                             -> SQLite history
                                                             -> terminal dashboard
                                                             -> web dashboard
                                                             -> JSON API

Exchange REST funding APIs -> FundingRateFetcher -> funding opportunity estimate
```

Main entry point:

```bash
python -m app.main
```

Start from here after downloading the archive: [START_HERE.md](START_HERE.md)

Practical run instructions: [RUNBOOK.md](RUNBOOK.md)

## Setup

Create and activate a virtual environment, then install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create local settings:

```bash
cp .env.example .env
```

Edit `.env` and fill only the values you need.

## Environment Variables

| Name | Default | Meaning |
|---|---:|---|
| `TELEGRAM_BOT_TOKEN` | empty | Telegram bot token. Optional. |
| `TELEGRAM_CHAT_ID` | empty | Telegram chat id. Optional. |
| `TRADING_SYMBOL` | `SOLUSDT` | Backward-compatible default symbol. |
| `TRADING_SYMBOLS` | `SOLUSDT,BTCUSDT,ETHUSDT` | Symbols subscribed by exchange adapters. |
| `DEFAULT_SYMBOL` | `SOLUSDT` | Symbol shown first in the dashboard. |
| `TRADING_BUDGET` | `500.0` | Budget used for estimated opportunity calculation. |
| `TAKER_FEE_RATE` | `0.001` | Simple taker fee estimate. `0.001` means 0.1%. |
| `MAX_PRICE_AGE_SECONDS` | `2.0` | Maximum age for a price to be considered fresh. |
| `WEB_HOST` | `localhost` | Dashboard host. |
| `WEB_PORT` | `8080` | Dashboard port. |
| `HISTORY_DB_PATH` | `data/market_history.sqlite3` | Local SQLite history path. |
| `HISTORY_FLUSH_INTERVAL_SECONDS` | `5.0` | How often snapshots/opportunities are saved. |
| `DEMO_MODE` | `false` | Use generated demo market data instead of live exchange WebSockets. |
| `MIN_SPREAD_PCT` | `0.0` | UI filter for minimum spread percentage. |
| `TELEGRAM_COMMANDS_ENABLED` | `false` | Enable Telegram polling commands. |
| `TELEGRAM_ALERT_MIN_SCORE` | `70.0` | Minimum opportunity score for Telegram alerts. |
| `TELEGRAM_ALERT_COOLDOWN_SECONDS` | `180` | Anti-spam cooldown for repeated alerts. |

Security rule: never commit `.env`. Keep `.env.example` fake and store real tokens only in local environment variables.

## Run

From the project folder:

```bash
python -m app.main
```

Open:

```text
http://localhost:8080
```

## JSON API

Health:

```text
GET /api/health?symbol=SOLUSDT
```

Available symbols:

```text
GET /api/symbols
```

Latest prices:

```text
GET /api/prices?symbol=SOLUSDT
```

Estimated opportunity:

```text
GET /api/opportunity?symbol=SOLUSDT
```

Order-book execution estimate:

```text
GET /api/execution?symbol=SOLUSDT&size=10
```

Recent opportunities:

```text
GET /api/opportunities?symbol=SOLUSDT&limit=20
```

History summary:

```text
GET /api/history?symbol=SOLUSDT
```

The opportunity endpoint returns an estimate based on top-of-book bid/ask. It is not an executable trading signal.

## FastAPI / Swagger

The realtime dashboard uses `aiohttp`, while the documented API can also be started through FastAPI:

```bash
uvicorn app.api.fastapi_app:app --reload --port 8000
```

Open:

```text
http://localhost:8000/docs
```

Useful FastAPI endpoints:

```text
GET /api/status
GET /api/symbols
GET /api/demo/opportunity?symbol=SOLUSDT
GET /api/demo/execution?symbol=SOLUSDT&size=10
GET /api/history?symbol=SOLUSDT
GET /api/opportunities?symbol=SOLUSDT
```

## Demo Mode

Demo mode works without exchange WebSockets. It uses generated market snapshots and is clearly marked as demo data.

In `.env`:

```env
DEMO_MODE=true
```

Then run:

```bash
python -m app.main
```

This is useful for project defense if Wi-Fi or exchange APIs are unavailable.

## Health Check

```bash
python -m scripts.check_health
```

This checks funding-rate REST APIs and exchange WebSocket streams.

## Dataset Export

SQLite history can be exported to CSV for later ML experiments:

```bash
python -m scripts.export_dataset --out data/opportunity_dataset.csv
```

Optional symbol filter:

```bash
python -m scripts.export_dataset --symbol SOLUSDT
```

The current model is an explainable scoring model. The export command prepares the data pipeline for a future trained model after enough real observations are collected.

## Telegram Commands

If Telegram is configured and `TELEGRAM_COMMANDS_ENABLED=true`, supported commands are:

```text
/menu
/status
/symbols
/prices SOLUSDT
/opportunity SOLUSDT
/execution SOLUSDT 10
/help
```

`/menu` opens inline buttons for quick status, prices, top-of-book opportunity, and order-book execution estimates.

Structured opportunity alerts are sent only when the signal is positive after fees, score is high enough, and cooldown allows it.

## Dashboard Languages

The web dashboard asks for a language on first visit and stores the choice in the browser.

- Russian docs: `http://localhost:8080/docs/ru`
- English docs: `http://localhost:8080/docs/en`

## Docker

```bash
docker compose up --build
```

Open:

```text
http://localhost:8080
```

## Tests

```bash
python -m unittest
```

Current tests focus on the most important calculation logic:

- stale prices are excluded;
- estimated profit subtracts taker fees.
- bid/ask opportunity calculation chooses lowest ask and highest bid;
- symbol normalization is tested;
- invalid bid/ask snapshots are rejected;
- FastAPI demo endpoint logic is tested;
- order-book execution VWAP, fees, slippage, stale filtering, and liquidity rejection are tested;
- ML baseline returns transparent quality labels;
- web API returns structured opportunity JSON.

## How to Explain This Project at Defense

Short version:

> This is an async Python backend service for crypto market analytics. It collects public bid/ask data from several exchanges, normalizes it, keeps the latest state in memory, scores potential cross-exchange opportunities, stores history in SQLite, and exposes both a web dashboard and JSON API. The app estimates possible cross-exchange anomalies and funding-rate opportunities, but it does not claim guaranteed profit because real execution depends on liquidity, deeper order-book depth, fees, slippage, and transfer constraints.

Important technical points:

- async IO is useful because the app waits on several network streams at the same time;
- each exchange has its own adapter because every exchange sends different JSON;
- shared state is kept in memory for the live dashboard;
- SQLite stores history for later analytics and future ML training;
- stale-data filtering is important because disconnected exchange data can create fake spreads;
- opportunity scoring is transparent and explainable;
- the ML module is currently a baseline quality classifier, not price prediction;
- `.env` keeps local secrets out of code;
- tests protect the calculation logic from accidental regressions.

## Current Limitations

- only a small symbol list is configured by default;
- live execution module uses REST order-book snapshots, not synchronized WebSocket deltas;
- visible order-book depth is modeled, but hidden liquidity is unknown;
- withdrawal/deposit fees are not modeled;
- funding opportunity logic is an estimate;
- ML is currently a heuristic baseline until enough SQLite history is collected;
- FastAPI is currently a documented companion API; the realtime WebSocket dashboard still runs on aiohttp.

These are normal limitations for a student MVP as long as they are explained honestly.
