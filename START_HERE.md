# Start Here

This file explains how to run the project after downloading or extracting the archive.

## Quick Start in Russian

Самый простой запуск после распаковки архива:

```bash
cd crypto-arbitrage-analytics
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
DEMO_MODE=true python -m app.main
```

Потом открыть:

```text
http://localhost:8080
```

Остановить проект:

```text
Ctrl + C
```

## What Is Included

The archive contains the source code, tests, documentation, Docker files, and `.env.example`.

The archive intentionally does not include local machine files:

- `.env` with private tokens;
- `.venv` virtual environment;
- `.git` commit history;
- `data/` local SQLite database;
- Python cache folders.

These files are not required in the submitted archive. They are created locally when the project is installed and run.

## Requirements

Use one of these options:

- Python 3.11 or newer;
- Docker Desktop.

Python is enough for the standard run. Docker is optional.

## Option 1: Run With Python

Open Terminal in the extracted project folder:

```bash
cd crypto-arbitrage-analytics
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the safe demo mode:

```bash
DEMO_MODE=true python -m app.main
```

Open the dashboard:

```text
http://localhost:8080
```

Stop the app:

```text
Ctrl + C
```

## Option 2: Run Live Exchange Mode

This connects to public exchange streams instead of generated demo data:

```bash
python -m app.main
```

Open:

```text
http://localhost:8080
```

If exchange APIs or Wi-Fi are unstable, use demo mode for presentation:

```bash
DEMO_MODE=true python -m app.main
```

## Option 3: Open Dashboard From Phone

Phone and computer must be on the same Wi-Fi.

Run:

```bash
HOME_SERVER_MODE=true DEMO_MODE=true python -m app.main
```

The terminal prints two links:

```text
Web Dashboard local: http://localhost:8080
Web Dashboard phone: http://192.168.x.x:8080
```

Open the `Web Dashboard phone` link on the phone.

Important: `localhost` works only on the computer. On the phone, use the printed `192.168...` address.

## Option 4: Run With Docker

Start Docker Desktop first.

Then run:

```bash
docker compose up --build
```

Open:

```text
http://localhost:8080
```

Stop:

```text
Ctrl + C
```

## Optional Telegram Setup

The project works without Telegram.

To enable Telegram notifications, create a local `.env` file from the example:

```bash
cp .env.example .env
```

Fill these values in `.env`:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

Telegram commands are optional. To enable them:

```env
TELEGRAM_COMMANDS_ENABLED=true
```

Useful commands in Telegram:

```text
/menu
/status
/opportunity SOLUSDT
/execution SOLUSDT 10
```

Do not publish real Telegram tokens.

## Tests

Run all tests:

```bash
python -m unittest
```

Expected result:

```text
Ran 17 tests
OK
```

## FastAPI Swagger Docs

The main dashboard runs with `app.main`.

The documented FastAPI app can also be started separately:

```bash
python -m uvicorn app.api.fastapi_app:app --reload --port 8000
```

Open:

```text
http://localhost:8000/docs
```

## Main Demo Scenario

For a stable project defense, use:

```bash
DEMO_MODE=true python -m app.main
```

Then open:

```text
http://localhost:8080
```

In the dashboard, show:

- language switch: Russian and English interface;
- market table across Binance, Bybit, OKX, and Gate.io;
- best spread panel;
- ML quality panel;
- order-book execution estimator;
- scenarios: profitable, slippage trap, low liquidity, and stale data;
- difference between raw spread and realistic net result.

## Common Problems

### `localhost:8080` does not open

Make sure the app is still running in Terminal. If it stopped, run it again:

```bash
DEMO_MODE=true python -m app.main
```

### Port 8080 is busy

Use another port:

```bash
WEB_PORT=8090 DEMO_MODE=true python -m app.main
```

Open:

```text
http://localhost:8090
```

### Dashboard says disconnected

Refresh the page. If it still says disconnected, stop the app with `Ctrl + C` and start it again.

### Docker cannot connect to daemon

Start Docker Desktop and wait until it is fully running. Then repeat:

```bash
docker compose up --build
```
