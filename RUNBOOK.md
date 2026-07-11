# How to Run the Project

This file is a practical runbook. Use it when you forget the exact commands.

## 1. Open Terminal in the Project Folder

```bash
cd /Users/amireleusizov/Downloads/first-_crypto-main/crypto-arbitrage-bot
```

If your terminal line starts with `(.venv)`, the virtual environment is already active. If not, activate it:

```bash
source .venv/bin/activate
```

## 2. Normal Live Run

This connects to real exchanges.

```bash
.venv/bin/python -m app.main
```

Open on Mac:

```text
http://localhost:8080
```

Stop:

```text
Ctrl + C
```

## 3. Demo Run Without Internet Exchanges

Use this for defense if Wi-Fi or exchange APIs are unstable.

```bash
DEMO_MODE=true .venv/bin/python -m app.main
```

Open:

```text
http://localhost:8080
```

## 4. Open Dashboard From Phone

Phone and Mac must be on the same Wi-Fi.

Run:

```bash
HOME_SERVER_MODE=true .venv/bin/python -m app.main
```

The app will print something like:

```text
Web Dashboard local: http://localhost:8080
Web Dashboard phone: http://192.168.1.45:8080
```

Open the `phone` URL on your phone.

If the app prints `LAN IP not detected`, find the Mac Wi-Fi IP manually:

```bash
ipconfig getifaddr en0
```

Then open on the phone:

```text
http://YOUR_MAC_IP:8080
```

Example:

```text
http://192.168.1.45:8080
```

## 5. Demo Mode From Phone

Best safe demo command:

```bash
HOME_SERVER_MODE=true DEMO_MODE=true .venv/bin/python -m app.main
```

Use this if you want to show the dashboard from your phone without relying on real exchange APIs.

## 6. If Port 8080 Is Busy

Use another port:

```bash
WEB_PORT=8090 .venv/bin/python -m app.main
```

Then open:

```text
http://localhost:8090
```

For phone + demo + port 8090:

```bash
HOME_SERVER_MODE=true DEMO_MODE=true WEB_PORT=8090 .venv/bin/python -m app.main
```

## 7. FastAPI / Swagger

This starts the documented API:

```bash
.venv/bin/python -m uvicorn app.api.fastapi_app:app --reload --port 8000
```

Open:

```text
http://localhost:8000/docs
```

Stop:

```text
Ctrl + C
```

## 8. Docker Run

Docker Desktop must be running first.

Start Docker Desktop:

```bash
open -a Docker
```

Check:

```bash
docker info
```

Run project:

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

## 9. Common Problems

### Docker says daemon is not running

Start Docker Desktop:

```bash
open -a Docker
```

Wait until Docker is fully started, then run Docker commands again.

### Phone cannot open the dashboard

Check:

- Mac and phone are on the same Wi-Fi.
- You started with `HOME_SERVER_MODE=true`.
- You opened the `Web Dashboard phone` URL printed by the app.
- VPN is off.
- macOS Firewall is not blocking Python.

### Address `localhost` does not work on phone

This is expected. On the phone, `localhost` means the phone itself, not the Mac.

Use the printed phone URL, for example:

```text
http://192.168.1.45:8080
```

### Telegram does not work

The project still works without Telegram. Telegram needs:

- real `TELEGRAM_BOT_TOKEN`;
- correct `TELEGRAM_CHAT_ID`;
- internet access;
- `TELEGRAM_COMMANDS_ENABLED=true` only if you want commands;
- `/menu` in Telegram to open interactive buttons;
- `/execution SOLUSDT 10` to request a realistic order-book execution estimate.

### Dashboard language

The dashboard shows a language choice on first visit:

- `RU` opens Russian labels and `/docs/ru`;
- `EN` opens English labels and `/docs/en`.

## 10. Recommended Defense Command

For a stable demonstration:

```bash
HOME_SERVER_MODE=true DEMO_MODE=true .venv/bin/python -m app.main
```

This gives:

- no dependency on real exchange APIs;
- dashboard available on Mac;
- dashboard available on phone;
- visible order-book execution estimate.
